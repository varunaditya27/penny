import json
import logging
import os
import time
from typing import Optional, Dict, Any

from code.data.evidence import tracker
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
        self.api_key = api_key if api_key is not None else os.environ.get("GROQ_API_KEY", "")
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
            "1. Output ONLY the single final explanation sentence. No explanations, no quotes, no markdown, no conversational filler.\n"
            "2. Follow the exact vocabulary, currency formatting, and style of the reference examples.\n"
            "3. Conclude with: 'This leaves at least {currency} {min_balance} available.'\n"
        )

        few_shots = [
            # request_06: single stop
            {
                "role": "user",
                "content": (
                    "Request: amount=620.40, currency=EUR, completion_date=2026-01-14\n"
                    "Profile: min_balance=800\n"
                    "Decision: method=full_payment, spending_changes=stop:event_476 (family streaming plan)"
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
                    "Request: amount=13,110,000, currency=IDR, completion_date=2025-06-12\n"
                    "Profile: min_balance=34,140,600\n"
                    "Decision: method=full_payment, spending_changes=reduce_to:event_989:665950 (weekend food delivery to IDR 665,950)"
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
                    "Request: amount=1,574.40, currency=USD, completion_date=2026-04-14\n"
                    "Profile: min_balance=1,800\n"
                    "Decision: method=full_payment, spending_changes=stop:event_1815 (online backup subscription) and reduce_to:event_1816:23.50 (streaming subscription to USD 23.50)"
                ),
            },
            {
                "role": "assistant",
                "content": "Stop the online backup subscription and reduce the streaming subscription to USD 23.50, then pay USD 1,574.40 today. This leaves at least USD 1,800 available.",
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
                clean_desc = ev_desc.strip().lower()
                if act_type == "stop":
                    changes_desc.append(f"stop:{ev_id} ({clean_desc})")
                elif act_type == "reduce_to":
                    new_val = parts[2] if len(parts) > 2 else "0"
                    try:
                        f_val = float(new_val)
                        formatted_new = format_currency_amount(f_val)
                    except ValueError:
                        formatted_new = new_val
                    changes_desc.append(
                        f"reduce_to:{ev_id}:{new_val} ({clean_desc} to {profile.home_currency} {formatted_new})"
                    )

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
        """Call Groq API over HTTP with error handling and retry for rate limits."""
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
            "reasoning_effort": "low",
            "max_tokens": 220,
        }

        max_retries = 3
        backoff = 2.0

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    GROQ_CHAT_COMPLETIONS_URL,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code == 429:
                    retry_after = float(response.headers.get("retry-after", backoff))
                    logger.warning(
                        f"Groq API 429 Rate Limit. Sleeping {retry_after}s before retry (attempt {attempt + 1}/{max_retries})."
                    )
                    time.sleep(retry_after)
                    backoff *= 1.5
                    continue

                response.raise_for_status()
                data = response.json()

                # Update usage metrics
                self.total_calls += 1
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)

                self.total_prompt_tokens += prompt_tokens
                self.total_completion_tokens += completion_tokens
                self.total_tokens += total_tokens

                # Record in global tracker for usage report
                tracker.record(self.model, prompt_tokens, completion_tokens)

                content = data["choices"][0]["message"].get("content", "").strip()
                # Clean narrow no-break space and non-breaking space
                content = content.replace("\u202f", " ").replace("\u00a0", " ")

                # Strip wrapping quotation marks if present
                if (content.startswith('"') and content.endswith('"')) or (
                    content.startswith("'") and content.endswith("'")
                ):
                    content = content[1:-1].strip()

                # Small delay to respect token-per-minute limits
                time.sleep(1.0)
                return content
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(backoff)
                backoff *= 1.5

        raise RuntimeError("Exceeded maximum retries for Groq API call.")

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
        is_complex = bool(
            plan.spending_changes_needed
            and plan.spending_changes_needed != "none"
        )
        should_call_llm = self.is_available and (
            force_llm or (use_llm_for_complex and is_complex)
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
            if (
                explanation
                and explanation.endswith(".")
                and profile.home_currency in explanation
                and "\n" not in explanation
                and not explanation.startswith("*")
                and not explanation.startswith("-")
            ):
                return explanation
            else:
                logger.warning(
                    f"Groq API returned malformed explanation: {repr(explanation)}; falling back to template."
                )
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
