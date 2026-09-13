import logging
from datetime import datetime
from typing import Optional, Dict, Any, Union, List

from backend.core.models.domain import UserProfile, PurchaseRequest, FinancialEvent
from backend.core.models.results import CandidatePlan, PaymentMethod, AffordabilityStatus

logger = logging.getLogger("buy_or_wait.explanations.templates")


def format_currency_amount(amount: Union[float, int, str]) -> str:
    """
    Format a currency amount with commas for thousands and exact decimals:
    - If whole number (or within 1e-4), formatted as integer with commas: 25256 -> '25,256', 18000 -> '18,000'
    - If non-zero fractional cents, formatted with 2 decimal places with commas: 620.4 -> '620.40', 15952906.67 -> '15,952,906.67'
    """
    if amount is None:
        return "0"
    try:
        val = float(amount)
    except (ValueError, TypeError):
        return str(amount)

    if abs(val - round(val)) < 1e-4:
        return f"{int(round(val)):,}"
    else:
        return f"{val:,.2f}"


def format_display_date(date_str: str) -> str:
    """
    Format a 'YYYY-MM-DD' date string into the exact sentence style:
    e.g. '2025-08-08' -> '8 August 2025', '2026-03-01' -> '1 March 2026'.
    Day has no leading zero, full month name, full 4-digit year.
    """
    if not date_str:
        return ""
    cleaned = str(date_str).strip()
    try:
        dt = datetime.strptime(cleaned, "%Y-%m-%d")
        return f"{dt.day} {dt.strftime('%B')} {dt.year}"
    except ValueError:
        return cleaned


def _clean_event_description(desc: str) -> str:
    """
    Normalize event description for embedding in a sentence clause:
    e.g. 'Family streaming plan' -> 'the family streaming plan'
    """
    cleaned = desc.strip()
    if cleaned.lower().startswith("the "):
        return cleaned.lower()
    return f"the {cleaned.lower()}"


def _extract_event_description(event_id: str, events_by_id: Optional[Dict[str, Any]]) -> str:
    """Extract description string from events lookup map."""
    if not events_by_id or event_id not in events_by_id:
        return f"expense {event_id}"
    item = events_by_id[event_id]
    if hasattr(item, "description"):
        return item.description
    elif isinstance(item, dict) and "description" in item:
        return item["description"]
    elif isinstance(item, str):
        return item
    return f"expense {event_id}"


def format_affordable_now(
    currency: str,
    amount: Union[float, int],
    min_balance: Union[float, int],
    keep_style: bool = False,
) -> str:
    """
    Template for affordable_now / full_payment:
    Default: 'Pay {currency} {amount} today. This leaves at least {currency} {min_balance} available over the next 90 days.'
    Keep style: 'Pay {currency} {amount} today. This keeps the {currency} {min_balance} minimum available over the next 90 days.'
    """
    amt_str = format_currency_amount(amount)
    min_str = format_currency_amount(min_balance)
    if keep_style:
        return f"Pay {currency} {amt_str} today. This keeps the {currency} {min_str} minimum available over the next 90 days."
    return f"Pay {currency} {amt_str} today. This leaves at least {currency} {min_str} available over the next 90 days."


def format_installments(
    n: int,
    currency: str,
    payment_amount: Union[float, int],
    first_payment_date: str,
    min_balance: Union[float, int],
) -> str:
    """
    Template for installments:
    'Use {n} installments of {currency} {payment_amount}, starting {first_payment_date_formatted}. This leaves at least {currency} {min_balance} available.'
    """
    amt_str = format_currency_amount(payment_amount)
    date_str = format_display_date(first_payment_date)
    min_str = format_currency_amount(min_balance)
    return f"Use {n} installments of {currency} {amt_str}, starting {date_str}. This leaves at least {currency} {min_str} available."


def format_wait(
    currency: str,
    amount: Union[float, int],
    earliest_date: str,
    min_balance: Union[float, int],
    wait_style: str = "pay_in_full",
) -> str:
    """
    Template for wait:
    pay_in_full (default): 'Pay {currency} {amount} in full on {earliest_date_formatted}. Paying earlier would take the balance below the {currency} {min_balance} minimum.'
    wait_until: 'Wait until {earliest_date_formatted}, then pay {currency} {amount} in full. Paying sooner would put the {currency} {min_balance} minimum at risk.'
    """
    amt_str = format_currency_amount(amount)
    date_str = format_display_date(earliest_date)
    min_str = format_currency_amount(min_balance)
    if wait_style == "wait_until":
        return f"Wait until {date_str}, then pay {currency} {amt_str} in full. Paying sooner would put the {currency} {min_str} minimum at risk."
    return f"Pay {currency} {amt_str} in full on {date_str}. Paying earlier would take the balance below the {currency} {min_str} minimum."


def format_partial_payment(
    currency: str,
    safe_amount: Union[float, int],
    remainder_amount: Union[float, int],
    earliest_date: str,
    min_balance: Union[float, int],
) -> str:
    """
    Template for partial_payment:
    'Pay {currency} {safe_amount} today and the remaining {currency} {remainder_amount} on {earliest_date_formatted}. This completes the full request and keeps the {currency} {min_balance} minimum protected.'
    """
    safe_str = format_currency_amount(safe_amount)
    rem_str = format_currency_amount(remainder_amount)
    date_str = format_display_date(earliest_date)
    min_str = format_currency_amount(min_balance)
    return (
        f"Pay {currency} {safe_str} today and the remaining {currency} {rem_str} on {date_str}. "
        f"This completes the full request and keeps the {currency} {min_str} minimum protected."
    )


def format_not_recommended(
    currency: str,
    amount: Union[float, int],
    min_balance: Union[float, int],
    safe_amount: Union[float, int] = 0.0,
    completion_date: str = "",
    plan_rejected_by_deadline: bool = False,
) -> str:
    """
    Template for not_recommended / not_affordable:
    If safe_amount > 0 and not plan_rejected_by_deadline:
        'Do not proceed with the {currency} {amount} request. Although {currency} {safe_amount} is available today, the full amount cannot be completed safely within 90 days.'
    If safe_amount == 0 or plan rejected by deadline:
        'Do not make this payment by {completion_date_formatted}. None of the available options keeps the {currency} {min_balance} minimum protected.'
    """
    amt_str = format_currency_amount(amount)
    safe_val = float(safe_amount) if safe_amount is not None else 0.0

    if safe_val > 0.0 and not plan_rejected_by_deadline:
        safe_str = format_currency_amount(safe_val)
        return (
            f"Do not proceed with the {currency} {amt_str} request. "
            f"Although {currency} {safe_str} is available today, the full amount cannot be completed safely within 90 days."
        )
    else:
        date_str = format_display_date(completion_date)
        min_str = format_currency_amount(min_balance)
        return f"Do not make this payment by {date_str}. None of the available options keeps the {currency} {min_str} minimum protected."


def format_spending_changes(
    spending_changes_needed: str,
    currency: str,
    amount: Union[float, int],
    min_balance: Union[float, int],
    events_by_id: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Template for affordable_with_plan with spending changes:
    - Single stop: 'Stop the {event_desc}, then pay {currency} {amount} today. This leaves at least {currency} {min_balance} available.'
    - Single reduce: 'Reduce the {event_desc} to {currency} {min_amt}, then pay {currency} {amount} today. This leaves at least {currency} {min_balance} available.'
    - Multiple changes: 'Stop the {desc1} and reduce the {desc2} to {currency} {min_amt}, then pay {currency} {amount} today. This leaves at least {currency} {min_balance} available.'
    """
    if not spending_changes_needed or spending_changes_needed == "none":
        return format_affordable_now(currency, amount, min_balance)

    actions = [act.strip() for act in spending_changes_needed.split("|") if act.strip()]
    clauses: List[str] = []

    for idx, act in enumerate(actions):
        parts = act.split(":")
        action_type = parts[0].strip()
        event_id = parts[1].strip() if len(parts) > 1 else ""
        raw_desc = _extract_event_description(event_id, events_by_id)
        desc_phrase = _clean_event_description(raw_desc)

        if action_type == "stop":
            verb = "Stop" if idx == 0 else "stop"
            clauses.append(f"{verb} {desc_phrase}")
        elif action_type == "reduce_to":
            new_amount_str = parts[2].strip() if len(parts) > 2 else "0"
            try:
                formatted_new = format_currency_amount(float(new_amount_str))
            except ValueError:
                formatted_new = new_amount_str
            verb = "Reduce" if idx == 0 else "reduce"
            clauses.append(f"{verb} {desc_phrase} to {currency} {formatted_new}")
        else:
            clauses.append(f"adjust {desc_phrase}")

    if len(clauses) == 1:
        combined = clauses[0]
    elif len(clauses) == 2:
        combined = f"{clauses[0]} and {clauses[1]}"
    else:
        first_part = ", ".join(clauses[:-1])
        combined = f"{first_part}, and {clauses[-1]}"

    amt_str = format_currency_amount(amount)
    min_str = format_currency_amount(min_balance)
    return f"{combined}, then pay {currency} {amt_str} today. This leaves at least {currency} {min_str} available."


class ExplanationTemplateSynthesizer:
    """
    Deterministic template synthesizer for Buy or Wait financial decision agent.
    Matches 100% of the sentence patterns found in dataset/sample_requests.csv.
    """

    @classmethod
    def synthesize(
        cls,
        plan: CandidatePlan,
        profile: Optional[UserProfile] = None,
        request: Optional[PurchaseRequest] = None,
        user: Optional[UserProfile] = None,
        events_by_id: Optional[Dict[str, Any]] = None,
        style: Optional[str] = None,
        plan_rejected_by_deadline: Optional[bool] = None,
    ) -> str:
        """
        Synthesizes a decision explanation from plan, user profile, and request.
        """
        prof = profile or user
        if not prof or not request:
            raise ValueError("profile/user and request must be provided")
        currency = prof.home_currency
        min_balance = prof.minimum_balance_to_keep
        requested_amount = request.requested_amount

        # 1. Check spending changes first
        if plan.spending_changes_needed and plan.spending_changes_needed != "none":
            return format_spending_changes(
                spending_changes_needed=plan.spending_changes_needed,
                currency=currency,
                amount=requested_amount,
                min_balance=min_balance,
                events_by_id=events_by_id,
            )

        # 2. Payment method dispatch
        method = plan.payment_method

        if method == PaymentMethod.FULL_PAYMENT or plan.affordability_status == AffordabilityStatus.AFFORDABLE_NOW:
            keep_style = (style == "keeps")
            return format_affordable_now(
                currency=currency,
                amount=requested_amount,
                min_balance=min_balance,
                keep_style=keep_style,
            )

        elif method == PaymentMethod.INSTALLMENTS:
            # Parse installment payment amount from plan
            payment_amount = requested_amount
            if plan.payment_plan and ":" in plan.payment_plan:
                try:
                    first_item = plan.payment_plan.split("|")[0]
                    payment_amount = float(first_item.split(":")[1])
                except (IndexError, ValueError):
                    pass
            n = plan.number_of_payments
            first_date = plan.first_payment_date or request.request_date
            return format_installments(
                n=n,
                currency=currency,
                payment_amount=payment_amount,
                first_payment_date=first_date,
                min_balance=min_balance,
            )

        elif method == PaymentMethod.WAIT or plan.affordability_status == AffordabilityStatus.AFFORDABLE_LATER:
            earliest_date = plan.earliest_date_for_full_payment or request.desired_completion_date
            wait_style = style if style in ["pay_in_full", "wait_until"] else "pay_in_full"
            return format_wait(
                currency=currency,
                amount=requested_amount,
                earliest_date=earliest_date,
                min_balance=min_balance,
                wait_style=wait_style,
            )

        elif method == PaymentMethod.PARTIAL_PAYMENT:
            safe_amt = plan.amount_safe_to_pay
            remainder_amt = requested_amount - safe_amt
            earliest_date = plan.earliest_date_for_full_payment or request.desired_completion_date
            return format_partial_payment(
                currency=currency,
                safe_amount=safe_amt,
                remainder_amount=remainder_amt,
                earliest_date=earliest_date,
                min_balance=min_balance,
            )

        elif method == PaymentMethod.NOT_RECOMMENDED or plan.affordability_status == AffordabilityStatus.NOT_AFFORDABLE:
            # Determine if plan was rejected by deadline
            rejected_by_deadline = plan_rejected_by_deadline
            if rejected_by_deadline is None:
                # If plan has completes_by_deadline == False, or safe_amount == 0
                if not plan.completes_by_deadline or plan.amount_safe_to_pay <= 0.0:
                    rejected_by_deadline = True
                else:
                    # Default: safe_amount > 0 and completes_by_deadline is True
                    rejected_by_deadline = False

            return format_not_recommended(
                currency=currency,
                amount=requested_amount,
                min_balance=min_balance,
                safe_amount=plan.amount_safe_to_pay,
                completion_date=request.desired_completion_date,
                plan_rejected_by_deadline=rejected_by_deadline,
            )

        # Fallback
        return format_affordable_now(currency, requested_amount, min_balance)
