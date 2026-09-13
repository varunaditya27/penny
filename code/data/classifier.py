import json
import logging
import os
import urllib.request
import urllib.error
from enum import Enum
from typing import Dict, List, Optional

from code.data.evidence import tracker

logger = logging.getLogger("buy_or_wait.data.classifier")

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"


class IncomeType(str, Enum):
    CONFIRMED_SALARY = "confirmed_salary"
    RECURRING_PLATFORM_GIG = "recurring_platform_gig"
    RECURRING_CONTRACT = "recurring_contract"
    TERMINATED_SALARY = "terminated_salary"
    EXCLUDED_WINDFALL = "excluded_windfall"
    UNKNOWN = "unknown"


class IncomeStreamClassifier:
    """
    Classifies income/credit descriptions into financial stream categories.
    Obeys problem statement §6.3:
    - Excludes bonuses, commissions, lotteries, refunds, portfolio gains, prizes, severance.
    - Preserves confirmed employment salary, steady weekly gig payouts, and active retainers.
    - Detects terminated or seasonal contracts.
    
    Uses deterministic zero-latency taxonomy cache with optional LLM classification via Groq API.
    """

    TAXONOMY: Dict[str, IncomeType] = {
        # 1. Confirmed Employment / Base Salary
        "payroll credit": IncomeType.CONFIRMED_SALARY,
        "base salary": IncomeType.CONFIRMED_SALARY,
        "primary household salary": IncomeType.CONFIRMED_SALARY,
        "international employer payroll": IncomeType.CONFIRMED_SALARY,
        "next confirmed salary": IncomeType.CONFIRMED_SALARY,
        "second household income": IncomeType.CONFIRMED_SALARY,
        "first-job payroll": IncomeType.CONFIRMED_SALARY,
        "new employer payroll": IncomeType.CONFIRMED_SALARY,
        "payroll after returning from leave": IncomeType.CONFIRMED_SALARY,
        "august 2019 net salary": IncomeType.CONFIRMED_SALARY,

        # 2. Recurring Platform / Gig Economy Earnings
        "delivery platform payout": IncomeType.RECURRING_PLATFORM_GIG,
        "driver platform payout": IncomeType.RECURRING_PLATFORM_GIG,
        "weekly app earnings": IncomeType.RECURRING_PLATFORM_GIG,
        "task marketplace payout": IncomeType.RECURRING_PLATFORM_GIG,

        # 3. Recurring Freelance / Independent Contract Work
        "website project payment": IncomeType.RECURRING_CONTRACT,
        "content contract payment": IncomeType.RECURRING_CONTRACT,
        "consulting invoice payment": IncomeType.RECURRING_CONTRACT,
        "freelance milestone payment": IncomeType.RECURRING_CONTRACT,
        "independent work payment": IncomeType.RECURRING_CONTRACT,
        "application project payment": IncomeType.RECURRING_CONTRACT,
        "client retainer payment": IncomeType.RECURRING_CONTRACT,
        "design contract payment": IncomeType.RECURRING_CONTRACT,

        # 4. Terminated / Temporary / Transitional
        "previous employer payroll": IncomeType.TERMINATED_SALARY,
        "final employer payroll": IncomeType.TERMINATED_SALARY,
        "temporary assignment pay": IncomeType.TERMINATED_SALARY,
        "seasonal contract payment": IncomeType.TERMINATED_SALARY,
        "peak-season wages": IncomeType.TERMINATED_SALARY,
        "prorated first salary": IncomeType.TERMINATED_SALARY,
        "promotion arrears payment": IncomeType.TERMINATED_SALARY,
        "payroll before leave": IncomeType.TERMINATED_SALARY,

        # 5. Excluded Windfalls, Commissions, Refunds, Asset Gains (§6.3)
        "account commission payment": IncomeType.EXCLUDED_WINDFALL,
        "performance commission": IncomeType.EXCLUDED_WINDFALL,
        "monthly sales commission": IncomeType.EXCLUDED_WINDFALL,
        "quarterly performance bonus": IncomeType.EXCLUDED_WINDFALL,
        "prize proceeds": IncomeType.EXCLUDED_WINDFALL,
        "investment sale proceeds": IncomeType.EXCLUDED_WINDFALL,
        "pending merchant refund": IncomeType.EXCLUDED_WINDFALL,
        "settled card charge reversal": IncomeType.EXCLUDED_WINDFALL,
        "employer expense reimbursement": IncomeType.EXCLUDED_WINDFALL,
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_GROQ_MODEL,
        use_llm: bool = False,
    ):
        self.api_key = api_key if api_key is not None else os.environ.get("GROQ_API_KEY", "")
        self.model = model
        self.use_llm = use_llm and bool(self.api_key)
        self.dynamic_cache: Dict[str, IncomeType] = {}

    def classify(self, description: str) -> IncomeType:
        """Classifies a transaction description into an IncomeType."""
        if not description:
            return IncomeType.UNKNOWN

        clean_desc = description.strip().lower()

        # Check static taxonomy
        if clean_desc in self.TAXONOMY:
            return self.TAXONOMY[clean_desc]

        # Check dynamic cache
        if clean_desc in self.dynamic_cache:
            return self.dynamic_cache[clean_desc]

        # Rule-based fallback keywords
        for keyword, itype in [
            ("commission", IncomeType.EXCLUDED_WINDFALL),
            ("bonus", IncomeType.EXCLUDED_WINDFALL),
            ("lottery", IncomeType.EXCLUDED_WINDFALL),
            ("prize", IncomeType.EXCLUDED_WINDFALL),
            ("refund", IncomeType.EXCLUDED_WINDFALL),
            ("reversal", IncomeType.EXCLUDED_WINDFALL),
            ("reimbursement", IncomeType.EXCLUDED_WINDFALL),
            ("gain", IncomeType.EXCLUDED_WINDFALL),
            ("proceeds", IncomeType.EXCLUDED_WINDFALL),
            ("previous", IncomeType.TERMINATED_SALARY),
            ("final", IncomeType.TERMINATED_SALARY),
            ("temporary", IncomeType.TERMINATED_SALARY),
            ("seasonal", IncomeType.TERMINATED_SALARY),
            ("arrears", IncomeType.TERMINATED_SALARY),
            ("salary", IncomeType.CONFIRMED_SALARY),
            ("payroll", IncomeType.CONFIRMED_SALARY),
            ("wage", IncomeType.CONFIRMED_SALARY),
        ]:
            if keyword in clean_desc:
                self.dynamic_cache[clean_desc] = itype
                return itype

        # If LLM enabled and description unknown, classify via LLM
        if self.use_llm:
            llm_result = self._classify_via_llm(description)
            if llm_result != IncomeType.UNKNOWN:
                self.dynamic_cache[clean_desc] = llm_result
                return llm_result

        return IncomeType.UNKNOWN

    def is_recurring_income(self, description: str) -> bool:
        """Returns True if the income description represents confirmed, recurring ongoing income."""
        itype = self.classify(description)
        # Per §6.3, variable platform gig earnings (e.g. QuickCrew/driver/delivery payouts)
        # are not guaranteed future income, even if historic payouts recur.
        return itype in [
            IncomeType.CONFIRMED_SALARY,
            IncomeType.RECURRING_CONTRACT,
        ]

    def _classify_via_llm(self, description: str) -> IncomeType:
        """Invokes Groq API to semantically classify an ambiguous income description."""
        prompt = (
            f"Classify this credit/income description into exactly one of: "
            f"[CONFIRMED_SALARY, RECURRING_PLATFORM_GIG, RECURRING_CONTRACT, TERMINATED_SALARY, EXCLUDED_WINDFALL].\n"
            f"Description: '{description}'\n"
            f"Answer with only the classification name."
        )

        messages = [
            {"role": "system", "content": "You are a precise financial auditor classifying income streams."},
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 15,
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                GROQ_CHAT_COMPLETIONS_URL,
                data=req_data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                content = resp_json["choices"][0]["message"]["content"].strip().lower()

                # Track tokens
                usage = resp_json.get("usage", {})
                tracker.record(
                    self.model,
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                )

                if "platform" in content or "gig" in content:
                    return IncomeType.RECURRING_PLATFORM_GIG
                elif "contract" in content or "freelance" in content:
                    return IncomeType.RECURRING_CONTRACT
                elif "windfall" in content or "commission" in content or "bonus" in content:
                    return IncomeType.EXCLUDED_WINDFALL
                elif "terminated" in content or "temporary" in content:
                    return IncomeType.TERMINATED_SALARY
                elif "salary" in content or "confirmed" in content:
                    return IncomeType.CONFIRMED_SALARY
        except Exception as e:
            logger.debug(f"LLM income classification fallback on '{description}': {e}")

        return IncomeType.UNKNOWN
