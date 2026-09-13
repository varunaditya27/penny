import logging
from datetime import datetime, timedelta
from typing import List, Optional

from code.models.domain import PaymentOption, PurchaseRequest, UserProfile
from code.models.results import AffordabilityStatus, CandidatePlan, PaymentMethod
from code.simulation.ledger import DailyLedger

logger = logging.getLogger("buy_or_wait.optimizer.candidates")


def format_plan_amount(amt: float) -> str:
    """
    Formats amounts for payment plans and spending changes:
    - If whole number, format as integer string without decimals.
    - If fractional, format with exactly two decimal places (e.g. '620.40', '166.61').
    """
    rounded = round(float(amt), 2)
    if abs(rounded - round(rounded)) < 1e-5:
        return str(int(round(rounded)))
    return f"{rounded:.2f}"


def generate_schedule_dates(first_date_str: str, count: int, freq_days: Optional[int]) -> List[str]:
    """Generates chronological YYYY-MM-DD date strings for an installment sequence."""
    step = freq_days if (freq_days is not None and freq_days > 0) else 30
    start_dt = datetime.strptime(first_date_str, "%Y-%m-%d")
    return [(start_dt + timedelta(days=i * step)).strftime("%Y-%m-%d") for i in range(count)]


class CandidateGenerator:
    """
    Generates valid, eligible CandidatePlan objects for a PurchaseRequest under given ledger conditions.
    Enforces user preferences, request constraints, and installment duration traps.
    """

    @classmethod
    def generate_full_payment_candidate(
        cls,
        request: PurchaseRequest,
        user: UserProfile,
        ledger: DailyLedger,
        spending_changes: str = "none",
        earliest_full_date: str = "",
        safe_amt_baseline: float = 0.0,
    ) -> Optional[CandidatePlan]:
        """
        Generates full payment today candidate if:
        1. User considers 'full_payment'
        2. Paying requested_amount on request_date is safe in ledger
        """
        if not user.will_consider("full_payment"):
            return None

        # Test safety on request_date
        test_payments = [(request.request_date, float(request.requested_amount))]
        test_ledger = DailyLedger(
            user=user,
            request_date=request.request_date,
            days=ledger.days,
            recurring_streams=ledger.recurring_streams,
            future_events=ledger.future_events,
            spending_modifications=spending_changes,
            candidate_payments=test_payments,
        )

        if not test_ledger.is_safe():
            return None

        plan_str = f"{request.request_date}:{format_plan_amount(request.requested_amount)}"
        has_changes = spending_changes != "none" and bool(spending_changes)
        status = AffordabilityStatus.AFFORDABLE_WITH_PLAN if has_changes else AffordabilityStatus.AFFORDABLE_NOW
        earliest = earliest_full_date if earliest_full_date else request.request_date

        return CandidatePlan(
            payment_method=PaymentMethod.FULL_PAYMENT,
            payment_plan=plan_str,
            first_payment_date=request.request_date,
            total_payable_amount=float(request.requested_amount),
            number_of_payments=1,
            spending_changes_needed=spending_changes,
            payment_option_id="none",
            completes_by_deadline=(request.request_date <= request.desired_completion_date),
            requires_spending_changes=has_changes,
            affordability_status=status,
            earliest_date_for_full_payment=request.request_date if status == AffordabilityStatus.AFFORDABLE_NOW else earliest,
            amount_safe_to_pay=safe_amt_baseline,
        )

    @classmethod
    def generate_partial_payment_candidate(
        cls,
        request: PurchaseRequest,
        user: UserProfile,
        ledger: DailyLedger,
        safe_amt_baseline: float,
        earliest_full_date: str,
        spending_changes: str = "none",
    ) -> Optional[CandidatePlan]:
        """
        Generates partial payment candidate per challenge specifications:
        1. Request allows partial payment
        2. User considers 'partial_payment'
        3. 0 < safe_amt_baseline < requested_amount
        4. earliest_full_date is non-empty and <= desired_completion_date
        5. Exactly two payments: safe_amt today, remainder on earliest_full_date
        """
        if not request.allows_partial_payment:
            return None
        if not user.will_consider("partial_payment"):
            return None
        if not (0.0 < safe_amt_baseline < float(request.requested_amount)):
            return None
        if not earliest_full_date or earliest_full_date <= request.request_date:
            return None

        remainder = round(float(request.requested_amount) - safe_amt_baseline, 2)
        payments = [
            (request.request_date, safe_amt_baseline),
            (earliest_full_date, remainder),
        ]

        test_ledger = DailyLedger(
            user=user,
            request_date=request.request_date,
            days=ledger.days,
            recurring_streams=ledger.recurring_streams,
            future_events=ledger.future_events,
            spending_modifications=spending_changes,
            candidate_payments=payments,
        )

        if not test_ledger.is_safe():
            return None

        plan_str = f"{request.request_date}:{format_plan_amount(safe_amt_baseline)}|{earliest_full_date}:{format_plan_amount(remainder)}"
        has_changes = spending_changes != "none" and bool(spending_changes)
        completes = earliest_full_date <= request.desired_completion_date

        return CandidatePlan(
            payment_method=PaymentMethod.PARTIAL_PAYMENT,
            payment_plan=plan_str,
            first_payment_date=request.request_date,
            total_payable_amount=float(request.requested_amount),
            number_of_payments=2,
            spending_changes_needed=spending_changes,
            payment_option_id="partial_payment",
            completes_by_deadline=completes,
            requires_spending_changes=has_changes,
            affordability_status=AffordabilityStatus.AFFORDABLE_WITH_PLAN,
            earliest_date_for_full_payment=earliest_full_date,
            amount_safe_to_pay=safe_amt_baseline,
        )

    @classmethod
    def generate_installment_candidates(
        cls,
        request: PurchaseRequest,
        user: UserProfile,
        options: List[PaymentOption],
        ledger: DailyLedger,
        spending_changes: str = "none",
        earliest_full_date: str = "",
        safe_amt_baseline: float = 0.0,
    ) -> List[CandidatePlan]:
        """
        Generates candidate plans for eligible installment options:
        1. Option payment_method is 'installments'
        2. User considers 'installments'
        3. user.max_installment_months is set and option.number_of_payments <= user.max_installment_months
        4. Simulates full installment schedule in ledger and verifies is_safe()
        """
        if not user.will_consider("installments"):
            return []
        if user.max_installment_months is None:
            return []

        candidates: List[CandidatePlan] = []

        for opt in options:
            if opt.payment_method != "installments":
                continue

            # Trap elimination: discard if number of payments or schedule span exceeds user preference cap
            span_days = (opt.number_of_payments - 1) * (opt.payment_frequency_days or 30)
            span_months = (span_days + 15) // 30
            if opt.number_of_payments > user.max_installment_months or span_months > user.max_installment_months:
                logger.debug(
                    f"Discarding option {opt.payment_option_id}: payments={opt.number_of_payments}, span_months={span_months} > cap {user.max_installment_months}"
                )
                continue

            dates = generate_schedule_dates(
                first_date_str=opt.first_payment_date,
                count=opt.number_of_payments,
                freq_days=opt.payment_frequency_days,
            )

            test_payments = [(d, opt.payment_amount) for d in dates]
            test_ledger = DailyLedger(
                user=user,
                request_date=request.request_date,
                days=ledger.days,
                recurring_streams=ledger.recurring_streams,
                future_events=ledger.future_events,
                spending_modifications=spending_changes,
                candidate_payments=test_payments,
            )

            plan_str = "|".join(f"{d}:{format_plan_amount(opt.payment_amount)}" for d in dates)
            last_date = dates[-1] if dates else opt.first_payment_date
            completes = last_date <= request.desired_completion_date
            has_changes = spending_changes != "none" and bool(spending_changes)

            # Check safety through the duration of the installment schedule
            if last_date in test_ledger.dates:
                end_idx = test_ledger.dates.index(last_date)
                is_safe = all(b >= user.minimum_balance_to_keep for b in test_ledger.balances[: end_idx + 1])
            else:
                is_safe = test_ledger.is_safe()

            if not is_safe:
                continue

            candidates.append(
                CandidatePlan(
                    payment_method=PaymentMethod.INSTALLMENTS,
                    payment_plan=plan_str,
                    first_payment_date=opt.first_payment_date,
                    total_payable_amount=float(opt.total_payable_amount),
                    number_of_payments=opt.number_of_payments,
                    spending_changes_needed=spending_changes,
                    payment_option_id=opt.payment_option_id,
                    completes_by_deadline=completes,
                    requires_spending_changes=has_changes,
                    affordability_status=AffordabilityStatus.AFFORDABLE_WITH_PLAN,
                    earliest_date_for_full_payment=earliest_full_date,
                    amount_safe_to_pay=safe_amt_baseline,
                )
            )

        return candidates

    @classmethod
    def generate_wait_candidate(
        cls,
        request: PurchaseRequest,
        user: UserProfile,
        earliest_full_date: str,
        safe_amt_baseline: float = 0.0,
    ) -> Optional[CandidatePlan]:
        """
        Generates wait candidate if:
        1. User considers 'full_payment'
        2. earliest_full_date is non-empty and > request_date
        """
        if not user.will_consider("full_payment"):
            return None
        if not earliest_full_date or earliest_full_date <= request.request_date:
            return None

        plan_str = f"{earliest_full_date}:{format_plan_amount(request.requested_amount)}"
        completes = earliest_full_date <= request.desired_completion_date

        return CandidatePlan(
            payment_method=PaymentMethod.WAIT,
            payment_plan=plan_str,
            first_payment_date=earliest_full_date,
            total_payable_amount=float(request.requested_amount),
            number_of_payments=1,
            spending_changes_needed="none",
            payment_option_id="wait",
            completes_by_deadline=completes,
            requires_spending_changes=False,
            affordability_status=AffordabilityStatus.AFFORDABLE_LATER,
            earliest_date_for_full_payment=earliest_full_date,
            amount_safe_to_pay=safe_amt_baseline,
        )

    @classmethod
    def generate_not_recommended_candidate(
        cls,
        request: PurchaseRequest,
        safe_amt_baseline: float = 0.0,
        earliest_full_date: str = "",
    ) -> CandidatePlan:
        """Fallback candidate when no payment approach is safe or feasible within constraints."""
        return CandidatePlan(
            payment_method=PaymentMethod.NOT_RECOMMENDED,
            payment_plan="none",
            first_payment_date="9999-12-31",
            total_payable_amount=float("inf"),
            number_of_payments=999,
            spending_changes_needed="none",
            payment_option_id="none",
            completes_by_deadline=False,
            requires_spending_changes=False,
            affordability_status=AffordabilityStatus.NOT_AFFORDABLE,
            earliest_date_for_full_payment=earliest_full_date,
            amount_safe_to_pay=safe_amt_baseline,
        )
