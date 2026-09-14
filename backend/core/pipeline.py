import logging
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional

from backend.core.data.currency import ExchangeRateConverter
from backend.core.data.evidence import EvidenceManager
from backend.core.data.linker import EventLinker
from backend.core.data.loader import DataLoader
from backend.core.data.classifier import IncomeStreamClassifier
from backend.core.explanations.llm import LLMExplanationGenerator
from backend.core.explanations.templates import ExplanationTemplateSynthesizer
from backend.core.models.domain import FinancialEvent, PaymentOption, PurchaseRequest, UserProfile
from backend.core.models.results import AffordabilityStatus, CandidatePlan, OutputRow, PaymentMethod
from backend.core.optimizer.candidates import CandidateGenerator, generate_schedule_dates
from backend.core.optimizer.ranker import PlanRanker
from backend.core.optimizer.spending import SpendingOptimizer
from backend.core.simulation.builder import SimulationLedgerBuilder
from backend.core.simulation.ledger import DailyLedger
from backend.core.simulation.recurrence import RecurrenceDetector, RecurringStream
from backend.core.simulation.safety import SafetyEngine

logger = logging.getLogger("buy_or_wait.pipeline")


class DecisionPipeline:
    """
    End-to-end Decision Pipeline for Penny financial affordability assistant.
    """

    def __init__(
        self,
        data_loader: Optional[DataLoader] = None,
        evidence_manager: Optional[EvidenceManager] = None,
        explanation_generator: Optional[LLMExplanationGenerator] = None,
        converter: Optional[ExchangeRateConverter] = None,
        use_llm: bool = True,
    ):
        self.loader = data_loader or DataLoader()
        self.evidence_mgr = evidence_manager or EvidenceManager()
        self.explanation_generator = explanation_generator or LLMExplanationGenerator()
        self.converter = converter or ExchangeRateConverter()
        self.use_llm = use_llm
        self.income_classifier = IncomeStreamClassifier(use_llm=use_llm)

    def _build_ledger(
        self,
        user: UserProfile,
        events: List[FinancialEvent],
        request_date: str,
        days: int = 90,
        candidate_payments: Optional[Any] = None,
    ) -> DailyLedger:
        return SimulationLedgerBuilder.build_ledger(
            user=user,
            events=events,
            request_date=request_date,
            days=days,
            candidate_payments=candidate_payments,
            converter=self.converter,
            evidence_mgr=self.evidence_mgr,
            income_classifier=self.income_classifier,
        )

    def _extract_recurring_salary_stream(
        self,
        user: UserProfile,
        request_date: str,
        hist_events: List[FinancialEvent],
        future_events: List[FinancialEvent],
        user_mutations: List[Dict],
    ) -> Optional[RecurringStream]:
        """
        Determines the confirmed ongoing recurring salary stream, if any.
        Obeys problem statement rules:
        - Exclude commissions, bonuses, lottery, refunds, portfolio gains.
        - Stop salary if message says STOP_INCOME or description says 'final' / 'seasonal'.
        - Use mode of day-of-month across historical payroll events.
        """
        return SimulationLedgerBuilder.extract_recurring_salary_stream(
            user=user,
            request_date=request_date,
            hist_events=hist_events,
            future_events=future_events,
            user_mutations=user_mutations,
            converter=self.converter,
            income_classifier=self.income_classifier,
        )
    def process_request(
        self,
        request: PurchaseRequest,
        user: UserProfile,
        user_events: List[FinancialEvent],
        payment_options: List[PaymentOption],
    ) -> OutputRow:
        """Processes a single purchase request and returns a fully compliant OutputRow."""
        # Build baseline simulation ledger via SimulationLedgerBuilder
        baseline_ledger = self._build_ledger(
            user=user,
            events=user_events,
            request_date=request.request_date,
            days=90,
        )
        streams = baseline_ledger.recurring_streams
        future_events = baseline_ledger.future_events

        earliest_full_date = SafetyEngine.find_earliest_full_payment_date(
            user=user,
            recurring_streams=streams,
            future_events=future_events,
            request_date=request.request_date,
            requested_amount=request.requested_amount,
            days=90,
            desired_completion_date=request.desired_completion_date,
            baseline_ledger=baseline_ledger,
        )
        amount_safe_to_pay = SafetyEngine.compute_safe_amount(baseline_ledger, request.requested_amount)
        if earliest_full_date == request.request_date and baseline_ledger.is_safe():
            amount_safe_to_pay = round(float(request.requested_amount), 2)

        # 6. Candidate Generation without spending changes
        candidates: List[CandidatePlan] = []

        # (a) Full payment today candidate
        full_cand = CandidateGenerator.generate_full_payment_candidate(
            request=request,
            user=user,
            ledger=baseline_ledger,
            spending_changes="none",
            earliest_full_date=earliest_full_date,
            safe_amt_baseline=amount_safe_to_pay,
        )
        if full_cand:
            candidates.append(full_cand)

        # (b) Partial payment candidate
        part_cand = CandidateGenerator.generate_partial_payment_candidate(
            request=request,
            user=user,
            ledger=baseline_ledger,
            safe_amt_baseline=amount_safe_to_pay,
            earliest_full_date=earliest_full_date,
            spending_changes="none",
        )
        if part_cand:
            candidates.append(part_cand)

        # (c) Installment candidates from available options
        inst_cands = CandidateGenerator.generate_installment_candidates(
            request=request,
            user=user,
            options=payment_options,
            ledger=baseline_ledger,
            spending_changes="none",
            earliest_full_date=earliest_full_date,
            safe_amt_baseline=amount_safe_to_pay,
        )
        candidates.extend(inst_cands)

        # (d) Wait candidate (if earliest date is safe and <= desired completion date)
        wait_cand = CandidateGenerator.generate_wait_candidate(
            request=request,
            user=user,
            earliest_full_date=earliest_full_date,
            safe_amt_baseline=amount_safe_to_pay,
        )
        if wait_cand:
            candidates.append(wait_cand)

        # Filter candidates that complete by desired_completion_date
        deadline_candidates = [c for c in candidates if c.completes_by_deadline]

        chosen_plan: Optional[CandidatePlan] = None

        events_map = {ev.event_id: ev for ev in user_events}

        if deadline_candidates:
            # Pick best plan that completes on time without spending changes
            chosen_plan = PlanRanker.select_best_plan(deadline_candidates)
        else:
            # No plan completes on time without changes; explore spending adjustments
            spending_plans = SpendingOptimizer.search_spending_plans(
                user=user,
                request=request,
                recurring_streams=streams,
                future_events=future_events,
                options=payment_options,
                safe_amt_baseline=amount_safe_to_pay,
                earliest_full_date=earliest_full_date,
                events_map=events_map,
            )
            deadline_spending = [c for c in spending_plans if c.completes_by_deadline]
            if deadline_spending:
                chosen_plan = PlanRanker.select_best_plan(deadline_spending)
            else:
                # Neither baseline nor spending adjustments can complete the request safely by deadline
                chosen_plan = CandidateGenerator.generate_not_recommended_candidate(
                    request=request,
                    safe_amt_baseline=amount_safe_to_pay,
                    earliest_full_date=earliest_full_date,
                )

        # 7. Synthesize explanation
        explanation = self.explanation_generator.generate_explanation(
            plan=chosen_plan,
            profile=user,
            request=request,
            events_by_id=events_map,
            use_llm_for_complex=self.use_llm,
        )

        return OutputRow(
            request_id=request.request_id,
            amount_safe_to_pay=amount_safe_to_pay,
            affordability_status=chosen_plan.affordability_status,
            recommended_payment_method=chosen_plan.payment_method,
            payment_plan=chosen_plan.payment_plan,
            earliest_date_for_full_payment=chosen_plan.earliest_date_for_full_payment,
            spending_changes_needed=chosen_plan.spending_changes_needed,
            decision_explanation=explanation,
        )
