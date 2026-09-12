import csv
import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from code.data.evidence import EvidenceManager
from code.data.linker import EventLinker
from code.data.loader import DataLoader
from code.explanations.llm import LLMExplanationGenerator
from code.explanations.templates import ExplanationTemplateSynthesizer
from code.models.domain import FinancialEvent, PaymentOption, PurchaseRequest, UserProfile
from code.models.results import AffordabilityStatus, CandidatePlan, OutputRow, PaymentMethod
from code.optimizer.candidates import CandidateGenerator, generate_schedule_dates
from code.optimizer.ranker import PlanRanker
from code.optimizer.spending import SpendingOptimizer
from code.simulation.ledger import DailyLedger
from code.simulation.recurrence import RecurrenceDetector, RecurringStream
from code.simulation.safety import SafetyEngine

logger = logging.getLogger("buy_or_wait.pipeline")


class DecisionPipeline:
    """
    End-to-end Decision Pipeline for Buy or Wait? financial decision agent.
    """

    NON_RECURRING_INCOME_KEYWORDS = {
        "commission",
        "bonus",
        "lottery",
        "refund",
        "gain",
        "portfolio",
        "unrealized",
        "valuation",
        "severance",
    }

    def __init__(
        self,
        data_loader: Optional[DataLoader] = None,
        evidence_manager: Optional[EvidenceManager] = None,
        explanation_generator: Optional[LLMExplanationGenerator] = None,
        use_llm: bool = True,
    ):
        self.loader = data_loader or DataLoader()
        self.evidence_mgr = evidence_manager or EvidenceManager()
        self.explanation_generator = explanation_generator or LLMExplanationGenerator()
        self.use_llm = use_llm

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
        stop_income = any(m.get("action") == "STOP_INCOME" for m in user_mutations)
        if stop_income:
            return None

        # Check for future scheduled salary
        sched_salaries = [
            e
            for e in future_events
            if e.category == "salary" or "salary" in e.description.lower() or "payroll" in e.description.lower()
        ]
        settled_salaries = [
            e
            for e in hist_events
            if (e.category == "salary" or "salary" in e.description.lower() or "payroll" in e.description.lower())
            and not any(k in e.description.lower() for k in self.NON_RECURRING_INCOME_KEYWORDS)
        ]

        if sched_salaries:
            sched = sorted(sched_salaries, key=lambda x: x.event_date)[-1]
            dom = int(sched.event_date.split("-")[2])
            return RecurringStream(
                description=sched.description,
                category="salary",
                cadence_type="dom",
                step_days=None,
                day_of_month=dom,
                baseline_amount=sched.amount,
                latest_date=sched.event_date,
                latest_event_id=sched.event_id,
                direction="credit",
            )

        if settled_salaries:
            latest_settled = sorted(settled_salaries, key=lambda x: x.event_date)[-1]
            desc = latest_settled.description.lower()
            if "final" in desc or "seasonal" in desc:
                # Terminated contract or final payroll
                return None

            # Calculate statistical mode of day of month across salary history
            doms = [int(e.event_date.split("-")[2]) for e in settled_salaries]
            mode_dom = Counter(doms).most_common(1)[0][0]

            amt = latest_settled.amount
            for m in user_mutations:
                if m.get("action") == "AMEND_SALARY" and m.get("amount"):
                    amt = float(m["amount"])

            return RecurringStream(
                description=latest_settled.description,
                category="salary",
                cadence_type="dom",
                step_days=None,
                day_of_month=mode_dom,
                baseline_amount=amt,
                latest_date=latest_settled.event_date,
                latest_event_id=latest_settled.event_id,
                direction="credit",
            )

        # Check for new job announced in messages
        for m in user_mutations:
            if m.get("action") in ["NEW_JOB", "NEW_JOB_SALARY"] and m.get("amount"):
                eff = m.get("effective_date", request_date)
                dom = int(eff.split("-")[2]) if "-" in eff else 15
                return RecurringStream(
                    description="Confirmed new employment salary",
                    category="salary",
                    cadence_type="dom",
                    step_days=None,
                    day_of_month=dom,
                    baseline_amount=float(m["amount"]),
                    latest_date=eff,
                    latest_event_id="msg_salary",
                    direction="credit",
                )

        return None

    def process_request(
        self,
        request: PurchaseRequest,
        user: UserProfile,
        user_events: List[FinancialEvent],
        payment_options: List[PaymentOption],
    ) -> OutputRow:
        """Processes a single purchase request and returns a fully compliant OutputRow."""
        # 1. Evidence reconciliation: apply image extractions and message mutations
        augmented_events = self.evidence_mgr.apply_evidence_to_events(
            events=user_events,
            user_id=user.user_id,
            request_date=request.request_date,
            home_currency=user.home_currency,
        )

        # 2. Partition events into historical settled and future/pending
        hist_events: List[FinancialEvent] = []
        future_events: List[FinancialEvent] = []

        for ev in augmented_events:
            # Skip non-cash, failed, cancelled, or unrealized investments
            if ev.is_non_cash or ev.status in ["failed", "cancelled", "unrealized"]:
                continue

            if ev.event_date <= request.request_date and ev.status == "settled":
                hist_events.append(ev)
            elif ev.status in ["pending", "scheduled"] or ev.event_date > request.request_date:
                future_events.append(ev)

        # 3. Detect recurring streams from historical settled events
        streams = RecurrenceDetector.detect_streams(hist_events)

        # Filter out all non-salary credit streams and commissions
        streams = [
            s
            for s in streams
            if not (
                s.is_credit
                and (
                    s.category != "salary"
                    or any(k in s.description.lower() for k in self.NON_RECURRING_INCOME_KEYWORDS)
                )
            )
        ]

        # 4. Integrate robust confirmed ongoing salary stream
        user_mutations = self.evidence_mgr.get_user_mutations(user.user_id, request.request_date)
        salary_stream = self._extract_recurring_salary_stream(
            user=user,
            request_date=request.request_date,
            hist_events=hist_events,
            future_events=future_events,
            user_mutations=user_mutations,
        )

        # Remove existing salary streams and add canonical salary stream if present
        streams = [s for s in streams if s.category != "salary"]
        if salary_stream is not None:
            streams.append(salary_stream)

        # 5. Baseline Simulation: compute safe amount & earliest full payment date
        baseline_ledger = DailyLedger(
            user=user,
            request_date=request.request_date,
            days=90,
            recurring_streams=streams,
            future_events=future_events,
        )

        amount_safe_to_pay = SafetyEngine.compute_safe_amount(baseline_ledger, request.requested_amount)
        earliest_full_date = SafetyEngine.find_earliest_full_payment_date(
            user=user,
            recurring_streams=streams,
            future_events=future_events,
            request_date=request.request_date,
            requested_amount=request.requested_amount,
            days=90,
            desired_completion_date=request.desired_completion_date,
        )

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
            )
            deadline_spending = [c for c in spending_plans if c.completes_by_deadline]
            if deadline_spending:
                chosen_plan = PlanRanker.select_best_plan(deadline_spending)
            elif wait_cand and earliest_full_date <= request.desired_completion_date:
                chosen_plan = wait_cand
            else:
                # Neither baseline nor spending adjustments can complete the request safely by deadline
                chosen_plan = CandidateGenerator.generate_not_recommended_candidate(
                    request=request,
                    safe_amt_baseline=amount_safe_to_pay,
                    earliest_full_date=earliest_full_date,
                )

        # 7. Synthesize explanation
        events_map = {ev.event_id: ev for ev in user_events}
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
