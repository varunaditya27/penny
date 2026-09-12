import json
import logging
import os
from typing import Optional, Dict, Any

from code.explanations.templates import (
    ExplanationTemplateSynthesizer,
    format_currency_amount,
    format_display_date,
    _extract_event_description,
)
from code.models.domain import UserProfile, PurchaseRequest
from code.models.results import CandidatePlan

logger = logging.getLogger("buy_or_wait.explanations.llm")

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"


class LLMExplanationGenerator:
    """
    LLM-powered explanation generator for complex cases using Groq API.
    Falls back gracefully to deterministic templates if GROQ_API_KEY is not set
    or if the API request fails.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_GROQ_MODEL,
        timeout: float = 10.0,
        fallback_synthesizer: Optional[ExplanationTemplateSynthesizer] = None,
    ):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.model = model
        self.timeout = timeout
        self.fallback_synthesizer = fallback_synthesizer or ExplanationTemplateSynthesizer()

        # Token and call accounting for usage_report.md
        self.total_calls: int = 0
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_tokens: int = 0
        self.failed_calls: int = 0

    @property
    def is_available(self) -> bool:
        """Returns True if GROQ_API_KEY is configured and non-empty."""
        return bool(self.api_key and self.api_key.strip())

    def get_usage_summary(self) -> Dict[str, Any]:
        """Returns metrics summary for evaluation reporting."""
        return {
            "model": self.model,
            "total_calls": self.total_calls,
            "failed_calls": self.failed_calls,
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
        }

    def _build_few_shot_messages(
        self,
        plan: CandidatePlan,
        profile: UserProfile,
        request: PurchaseRequest,
        events_by_id: Optional[Dict[str, Any]],
    ) -> list:
        system_prompt = (
            "You are the explanation synthesizer for the Buy or Wait AI financial decision agent.\n"
            "Your task is to generate a single concise, grounded decision explanation sentence.\n"
            "Strict Rules:\n"
            "1. Output ONLY the single final explanation sentence. No explanations, no quotes, no conversational filler.\n"
            "2. Follow the exact vocabulary, currency formatting, and style of the reference examples.\n"
            "3. State the action, relevant amounts/dates, and minimum balance impact clearly.\n"
        )

        few_shots = [
            # request_06: single stop
            {
                "role": "user",
                "content": (
                    "Request: amount=620.40, currency=EUR, completion_date=2026-01-14\n"
                    "Profile: min_balance=800\n"
                    "Decision: method=full_payment, spending_changes=stop:event_476 (Family streaming plan)"
                ),
            },
            {
                "role": "assistant",
                "content": "Stop the family streaming plan, then pay EUR 620.40 today. This leaves at least EUR 800 available.",
            },
            # request_11: single reduce
            {
                "role": "user",
                "content": (
                    "Request: amount=13110000, currency=IDR, completion_date=2025-06-12\n"
                    "Profile: min_balance=34140600\n"
                    "Decision: method=full_payment, spending_changes=reduce_to:event_989:665950 (Weekend food delivery to IDR 665,950)"
                ),
            },
            {
                "role": "assistant",
                "content": "Reduce the weekend food delivery to IDR 665,950, then pay IDR 13,110,000 today. This leaves at least IDR 34,140,600 available.",
            },
            # request_21: multiple spending changes
            {
                "role": "user",
                "content": (
                    "Request: amount=1574.40, currency=USD, completion_date=2026-04-14\n"
                    "Profile: min_balance=1800\n"
                    "Decision: method=full_payment, spending_changes=stop:event_1815 (Online backup subscription) and reduce_to:event_1816:23.50 (Streaming subscription to USD 23.50)"
                ),
            },
            {
                "role": "assistant",
                "content": "Stop the online backup subscription and reduce the streaming subscription to USD 23.50, then pay USD 1,574.40 today. This leaves at least USD 1,800 available.",
            },
            # request_02: installments
            {
                "role": "user",
                "content": (
                    "Request: amount=46018000, currency=IDR, completion_date=2025-10-10\n"
                    "Profile: min_balance=29158400\n"
                    "Decision: method=installments, 3 installments of IDR 15,952,906.67 starting 2025-08-08"
                ),
            },
            {
                "role": "assistant",
                "content": "Use 3 installments of IDR 15,952,906.67, starting 8 August 2025. This leaves at least IDR 29,158,400 available.",
            },
            # request_03: wait
            {
                "role": "user",
                "content": (
                    "Request: amount=5491000, currency=IDR, completion_date=2019-11-15\n"
                    "Profile: min_balance=2668700\n"
                    "Decision: method=wait, earliest_full_payment_date=2019-11-15"
                ),
            },
            {
                "role": "assistant",
                "content": "Pay IDR 5,491,000 in full on 15 November 2019. Paying earlier would take the balance below the IDR 2,668,700 minimum.",
            },
        ]

        # Build current query
        changes_desc = []
        if plan.spending_changes_needed and plan.spending_changes_needed != "none":
            for act in plan.spending_changes_needed.split("|"):
                parts = act.split(":")
                act_type = parts[0]
                ev_id = parts[1] if len(parts) > 1 else ""
                ev_desc = _extract_event_description(ev_id, events_by_id)
                if act_type == "stop":
                    changes_desc.append(f"stop:{ev_id} ({ev_desc})")
                elif act_type == "reduce_to":
                    new_val = parts[2] if len(parts) > 2 else "0"
                    changes_desc.append(f"reduce_to:{ev_id}:{new_val} ({ev_desc} to {profile.home_currency} {new_val})")

        changes_summary = " and ".join(changes_desc) if changes_desc else "none"

        current_prompt = (
            f"Request: amount={format_currency_amount(request.requested_amount)}, currency={profile.home_currency}, completion_date={request.desired_completion_date}\n"
            f"Profile: min_balance={format_currency_amount(profile.minimum_balance_to_keep)}\n"
            f"Decision: method={plan.payment_method}, safe_amount={format_currency_amount(plan.amount_safe_to_pay)}, spending_changes={changes_summary}, payment_plan={plan.payment_plan}"
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(few_shots)
        messages.append({"role": "user", "content": current_prompt})
        return messages

    def _call_groq_api(self, messages: list) -> str:
        """Call Groq API over HTTP with error handling."""
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 120,
        }

        response = requests.post(
            GROQ_CHAT_COMPLETIONS_URL,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        # Update usage metrics
        self.total_calls += 1
        usage = data.get("usage", {})
        self.total_prompt_tokens += usage.get("prompt_tokens", 0)
        self.total_completion_tokens += usage.get("completion_tokens", 0)
        self.total_tokens += usage.get("total_tokens", 0)

        content = data["choices"][0]["message"]["content"].strip()
        # Strip wrapping quotation marks if present
        if (content.startswith('"') and content.endswith('"')) or (
            content.startswith("'") and content.endswith("'")
        ):
            content = content[1:-1].strip()
        return content

    def generate_explanation(
        self,
        plan: CandidatePlan,
        profile: UserProfile,
        request: PurchaseRequest,
        events_by_id: Optional[Dict[str, Any]] = None,
        force_llm: bool = False,
        use_llm_for_complex: bool = False,
        **kwargs,
    ) -> str:
        """
        Generate decision explanation.
        If GROQ_API_KEY is unset or conditions for LLM are not met,
        gracefully uses deterministic templates.
        """
        # 1. Check if LLM should be invoked
        should_call_llm = self.is_available and (
            force_llm
            or (
                use_llm_for_complex
                and plan.spending_changes_needed
                and plan.spending_changes_needed != "none"
                and "|" in plan.spending_changes_needed
            )
        )

        if not should_call_llm:
            logger.debug("Using deterministic template synthesizer.")
            return self.fallback_synthesizer.synthesize(
                plan=plan,
                profile=profile,
                request=request,
                events_by_id=events_by_id,
                **kwargs,
            )

        # 2. Invoke Groq API
        try:
            messages = self._build_few_shot_messages(
                plan=plan,
                profile=profile,
                request=request,
                events_by_id=events_by_id,
            )
            explanation = self._call_groq_api(messages)
            if explanation:
                return explanation
        except Exception as err:
            self.failed_calls += 1
            logger.warning(
                f"Groq API call failed ({type(err).__name__}: {err}); falling back to deterministic template."
            )

        # 3. Fallback to deterministic template
        return self.fallback_synthesizer.synthesize(
            plan=plan,
            profile=profile,
            request=request,
            events_by_id=events_by_id,
            **kwargs,
        )
