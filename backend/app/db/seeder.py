import csv
import logging
import os
import sys
from typing import Dict, Optional
from sqlalchemy.orm import Session

from backend.app.db.models import FinancialEventDB, PaymentOptionDB, UserDB
from backend.app.db.session import Base, SessionLocal, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("penny.db.seeder")


def seed_database_from_dataset(
    db: Session,
    dataset_dir: str = "dataset",
    limit_users: Optional[int] = None,
) -> Dict[str, int]:
    """
    Populates database from dataset CSV files:
    - dataset/financial_profiles.csv -> UserDB
    - dataset/financial_events.csv -> FinancialEventDB
    - dataset/request_payment_options.csv -> PaymentOptionDB
    """
    profiles_path = os.path.join(dataset_dir, "financial_profiles.csv")
    events_path = os.path.join(dataset_dir, "financial_events.csv")
    options_path = os.path.join(dataset_dir, "request_payment_options.csv")

    user_count = 0
    allowed_user_ids = set()

    if not os.path.exists(profiles_path):
        raise FileNotFoundError(f"Profiles dataset not found at {profiles_path}")

    with open(profiles_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row["user_id"]
            if limit_users and user_count >= limit_users:
                break

            allowed_user_ids.add(uid)
            existing = db.query(UserDB).filter_by(user_id=uid).first()
            if not existing:
                max_inst = int(row["max_installment_months"]) if row.get("max_installment_months") else None
                user = UserDB(
                    user_id=uid,
                    home_currency=row["home_currency"],
                    current_available_balance=float(row["current_available_balance"]),
                    minimum_balance_to_keep=float(row["minimum_balance_to_keep"]),
                    financial_priorities=row.get("financial_priorities", ""),
                    expense_categories_to_protect=row.get("expense_categories_to_protect", ""),
                    expense_categories_to_reduce=row.get("expense_categories_to_reduce", ""),
                    expense_categories_to_stop=row.get("expense_categories_to_stop", ""),
                    payment_methods_user_will_consider=row.get("payment_methods_user_will_consider", ""),
                    max_installment_months=max_inst,
                )
                db.add(user)
                user_count += 1
            else:
                user_count += 1
    db.commit()

    event_count = 0
    if os.path.exists(events_path):
        with open(events_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row["user_id"]
                if allowed_user_ids and uid not in allowed_user_ids:
                    continue

                ev_id = row["event_id"]
                existing_ev = db.query(FinancialEventDB).filter_by(event_id=ev_id).first()
                if not existing_ev:
                    amt = float(row["amount"]) if row.get("amount") else None
                    min_amt = float(row["minimum_allowed_amount"]) if row.get("minimum_allowed_amount") else None
                    event = FinancialEventDB(
                        event_id=ev_id,
                        user_id=uid,
                        event_type=row["event_type"],
                        description=row["description"],
                        category=row["category"],
                        direction=row["direction"],
                        amount=amt,
                        currency=row["currency"],
                        event_date=row["event_date"],
                        settlement_date=row.get("settlement_date") or None,
                        status=row["status"],
                        linked_event_id=row.get("linked_event_id") or None,
                        flexibility=row.get("flexibility", "fixed"),
                        minimum_allowed_amount=min_amt,
                    )
                    db.add(event)
                    event_count += 1
        db.commit()

    option_count = 0
    if os.path.exists(options_path):
        with open(options_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                opt_id = row["payment_option_id"]
                existing_opt = db.query(PaymentOptionDB).filter_by(payment_option_id=opt_id).first()
                if not existing_opt:
                    raw_freq = row.get("payment_frequency_days", "")
                    freq = int(raw_freq.strip()) if raw_freq and raw_freq.strip() else None
                    opt = PaymentOptionDB(
                        payment_option_id=opt_id,
                        request_id=row["request_id"],
                        payment_method=row["payment_method"],
                        payment_amount=float(row["payment_amount"]),
                        number_of_payments=int(row["number_of_payments"]),
                        first_payment_date=row["first_payment_date"],
                        payment_frequency_days=freq,
                        financing_fee=float(row.get("financing_fee", 0.0) or 0.0),
                        total_payable_amount=float(row["total_payable_amount"]),
                    )
                    db.add(opt)
                    option_count += 1
        db.commit()

    logger.info(f"Seeded {user_count} users, {event_count} new events, {option_count} new options.")
    return {"users": user_count, "events": event_count, "options": option_count}


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        dataset_dir = "dataset"
        if len(sys.argv) > 1:
            dataset_dir = sys.argv[1]
        counts = seed_database_from_dataset(db, dataset_dir=dataset_dir)
        print(f"Database successfully seeded: {counts}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
