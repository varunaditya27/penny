import csv
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set

from backend.core.models.domain import (
    FinancialEvent,
    PaymentOption,
    PurchaseRequest,
    UserProfile,
)
from backend.core.models.results import OutputRow

logger = logging.getLogger(__name__)


class DataLoader:
    """Production-grade loader for all Buy or Wait financial datasets with

    strict typing, robust parsing, and sample user isolation enforcement.
    """

    SAMPLE_USERS: Set[str] = {f"user_{i:02d}" for i in range(1, 26)}

    def __init__(self, data_dir: str = "dataset") -> None:
        self.data_dir = data_dir

    @classmethod
    def load_profiles(
        cls,
        path: str = "dataset/financial_profiles.csv",
        exclude_sample: bool = False,
    ) -> Dict[str, UserProfile]:
        """Load financial profiles from CSV.

        Args:
            path: Path to financial_profiles.csv.
            exclude_sample: If True, filters out sample users (user_01..user_25).

        Returns:
            Dict mapping user_id to UserProfile.
        """
        profiles: Dict[str, UserProfile] = {}
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_id = row["user_id"].strip()
                if exclude_sample and user_id in cls.SAMPLE_USERS:
                    continue

                priorities = [
                    p.strip()
                    for p in row.get("financial_priorities", "").split("|")
                    if p.strip()
                ]
                protect = {
                    p.strip()
                    for p in row.get("expense_categories_to_protect", "").split("|")
                    if p.strip()
                }
                reduce_cat = {
                    p.strip()
                    for p in row.get("expense_categories_user_is_willing_to_reduce", "").split("|")
                    if p.strip()
                }
                stop_cat = {
                    p.strip()
                    for p in row.get("expense_categories_user_is_willing_to_stop", "").split("|")
                    if p.strip()
                }
                methods = {
                    p.strip()
                    for p in row.get("payment_methods_user_will_consider", "").split("|")
                    if p.strip()
                }

                raw_max_inst = row.get("max_installment_months", "")
                max_inst = int(raw_max_inst.strip()) if raw_max_inst and raw_max_inst.strip() else None

                profile = UserProfile(
                    user_id=user_id,
                    home_currency=row["home_currency"].strip(),
                    current_available_balance=float(row["current_available_balance"].strip()),
                    minimum_balance_to_keep=float(row["minimum_balance_to_keep"].strip()),
                    financial_priorities=priorities,
                    expense_categories_to_protect=protect,
                    expense_categories_user_is_willing_to_reduce=reduce_cat,
                    expense_categories_user_is_willing_to_stop=stop_cat,
                    payment_methods_user_will_consider=methods,
                    max_installment_months=max_inst,
                )
                profiles[user_id] = profile

        return profiles

    @classmethod
    def load_requests(
        cls,
        path: str = "dataset/requests.csv",
    ) -> List[PurchaseRequest]:
        """Load evaluation purchase requests from CSV.

        Enforces sample isolation: guarantees no sample users (user_01..user_25) are present.
        """
        requests: List[PurchaseRequest] = []
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_id = row["user_id"].strip()
                if user_id in cls.SAMPLE_USERS:
                    raise ValueError(
                        f"Sample isolation violation: sample user '{user_id}' found in evaluation requests at {path}"
                    )

                req = PurchaseRequest(
                    request_id=row["request_id"].strip(),
                    user_id=user_id,
                    request_date=row["request_date"].strip(),
                    request_type=row["request_type"].strip(),
                    requested_amount=float(row["requested_amount"].strip()),
                    desired_completion_date=row["desired_completion_date"].strip(),
                    allows_partial_payment=row["allows_partial_payment"].strip().lower() in ("true", "1"),
                    request_text=row.get("request_text", "").strip(),
                )
                requests.append(req)

        return requests

    @classmethod
    def load_sample_requests(
        cls,
        path: str = "dataset/sample_requests.csv",
    ) -> List[PurchaseRequest]:
        """Load benchmark sample purchase requests from CSV.

        Enforces sample isolation: guarantees all requests belong exclusively to sample users.
        """
        requests: List[PurchaseRequest] = []
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_id = row["user_id"].strip()
                if user_id not in cls.SAMPLE_USERS:
                    raise ValueError(
                        f"Sample isolation violation: non-sample user '{user_id}' found in sample requests at {path}"
                    )

                req = PurchaseRequest(
                    request_id=row["request_id"].strip(),
                    user_id=user_id,
                    request_date=row["request_date"].strip(),
                    request_type=row["request_type"].strip(),
                    requested_amount=float(row["requested_amount"].strip()),
                    desired_completion_date=row["desired_completion_date"].strip(),
                    allows_partial_payment=row["allows_partial_payment"].strip().lower() in ("true", "1"),
                    request_text=row.get("request_text", "").strip(),
                )
                requests.append(req)

        return requests

    @classmethod
    def load_sample_ground_truth(
        cls,
        path: str = "dataset/sample_requests.csv",
    ) -> Dict[str, OutputRow]:
        """Load benchmark ground truth output rows from sample_requests.csv."""
        ground_truth: Dict[str, OutputRow] = {}
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                req_id = row["request_id"].strip()
                ground_truth[req_id] = OutputRow(
                    request_id=req_id,
                    amount_safe_to_pay=float(row["amount_safe_to_pay"].strip()),
                    affordability_status=row["affordability_status"].strip(),
                    recommended_payment_method=row["recommended_payment_method"].strip(),
                    payment_plan=row["payment_plan"].strip(),
                    earliest_date_for_full_payment=row.get("earliest_date_for_full_payment", "").strip(),
                    spending_changes_needed=row.get("spending_changes_needed", "none").strip(),
                    decision_explanation=row.get("decision_explanation", "").strip(),
                )
        return ground_truth

    @classmethod
    def load_events(
        cls,
        path: str = "dataset/financial_events.csv",
        user_id: Optional[str] = None,
        exclude_sample: bool = False,
    ) -> List[FinancialEvent]:
        """Load financial events with proper type coercion and optional filtering.

        Args:
            path: Path to financial_events.csv.
            user_id: Optional filter for a specific user.
            exclude_sample: If True, filters out sample users (user_01..user_25).
        """
        events: List[FinancialEvent] = []
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row["user_id"].strip()
                if user_id and uid != user_id:
                    continue
                if exclude_sample and uid in cls.SAMPLE_USERS:
                    continue

                raw_amt = row.get("amount", "")
                amount = float(raw_amt.strip()) if raw_amt and raw_amt.strip() else None

                raw_min = row.get("minimum_allowed_amount", "")
                min_amt = float(raw_min.strip()) if raw_min and raw_min.strip() else None

                event = FinancialEvent(
                    event_id=row["event_id"].strip(),
                    user_id=uid,
                    event_type=row["event_type"].strip(),
                    description=row.get("description", "").strip(),
                    category=row.get("category", "").strip(),
                    direction=row["direction"].strip(),
                    amount=amount,
                    currency=row.get("currency", "").strip(),
                    event_date=row["event_date"].strip(),
                    settlement_date=row.get("settlement_date", "").strip(),
                    status=row["status"].strip(),
                    linked_event_id=row.get("linked_event_id", "").strip(),
                    flexibility=row.get("flexibility", "fixed").strip() if row.get("flexibility") else "fixed",
                    minimum_allowed_amount=min_amt,
                )
                events.append(event)

        return events

    @classmethod
    def load_payment_options(
        cls,
        path: str = "dataset/request_payment_options.csv",
    ) -> Dict[str, List[PaymentOption]]:
        """Load request payment options, grouped by request_id."""
        options_by_req: Dict[str, List[PaymentOption]] = defaultdict(list)
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                req_id = row["request_id"].strip()
                raw_freq = row.get("payment_frequency_days", "")
                freq = int(raw_freq.strip()) if raw_freq and raw_freq.strip() else None

                raw_fee = row.get("financing_fee", "")
                fee = float(raw_fee.strip()) if raw_fee and raw_fee.strip() else 0.0

                opt = PaymentOption(
                    payment_option_id=row["payment_option_id"].strip(),
                    request_id=req_id,
                    payment_method=row["payment_method"].strip(),
                    payment_amount=float(row["payment_amount"].strip()),
                    number_of_payments=int(row["number_of_payments"].strip()),
                    first_payment_date=row["first_payment_date"].strip(),
                    payment_frequency_days=freq,
                    financing_fee=fee,
                    total_payable_amount=float(row["total_payable_amount"].strip()),
                )
                options_by_req[req_id].append(opt)

        return dict(options_by_req)
