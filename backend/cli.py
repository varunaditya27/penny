import argparse
import csv
import logging
import os
import sys

from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

from backend.core.data.evidence import EvidenceManager, tracker
from backend.core.data.loader import DataLoader
from backend.core.models.results import OutputRow
from backend.core.pipeline import DecisionPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("penny.cli")


def run_pipeline(
    sample_mode: bool = False,
    output_path: Optional[str] = None,
    tolerance: float = 5.0,
    use_llm: Optional[bool] = None,
) -> None:
    if output_path is None:
        output_path = "evaluation/sample_output.csv" if sample_mode else "output.csv"

    if use_llm is None:
        use_llm = False

    loader = DataLoader()
    evidence_mgr = EvidenceManager()
    pipeline = DecisionPipeline(
        data_loader=loader,
        evidence_manager=evidence_mgr,
        use_llm=use_llm,
    )

    profiles = loader.load_profiles()
    events = loader.load_events()
    payment_options = loader.load_payment_options()

    events_by_user = {}
    for ev in events:
        events_by_user.setdefault(ev.user_id, []).append(ev)

    if sample_mode:
        requests = loader.load_sample_requests()
        logger.info(f"Loaded {len(requests)} sample requests for calibration/evaluation.")
    else:
        requests = loader.load_requests()
        logger.info(f"Loaded {len(requests)} production evaluation requests.")

    output_rows: List[OutputRow] = []
    dict_rows = []

    for req in requests:
        user = profiles[req.user_id]
        u_events = events_by_user.get(req.user_id, [])
        u_options = payment_options.get(req.request_id, [])

        row = pipeline.process_request(
            request=req,
            user=user,
            user_events=u_events,
            payment_options=u_options,
        )
        output_rows.append(row)
        dict_rows.append({
            "request_id": row.request_id,
            "amount_safe_to_pay": str(row.amount_safe_to_pay),
            "affordability_status": row.affordability_status,
            "recommended_payment_method": row.recommended_payment_method,
            "payment_plan": row.payment_plan,
            "earliest_date_for_full_payment": row.earliest_date_for_full_payment,
            "spending_changes_needed": row.spending_changes_needed,
            "decision_explanation": row.decision_explanation,
        })

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fieldnames = [
        "request_id",
        "amount_safe_to_pay",
        "affordability_status",
        "recommended_payment_method",
        "payment_plan",
        "earliest_date_for_full_payment",
        "spending_changes_needed",
        "decision_explanation",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dict_rows)

    logger.info(f"Successfully wrote {len(dict_rows)} rows to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Penny AI-powered financial decision agent CLI.")
    parser.add_argument("--eval-sample", action="store_true", help="Run evaluation on dataset/sample_requests.csv")
    parser.add_argument("--tolerance", type=float, default=5.0, help="Numerical tolerance for safe amount")
    parser.add_argument("--output", type=str, default=None, help="Path to write output CSV")
    parser.add_argument("--use-llm", action="store_true", default=None, help="Explicitly enable LLM explanation calls via Groq API")
    parser.add_argument("--no-llm", dest="use_llm", action="store_false", help="Disable LLM calls and use deterministic templates only")

    args = parser.parse_args()
    run_pipeline(
        sample_mode=args.eval_sample,
        output_path=args.output,
        tolerance=args.tolerance,
        use_llm=args.use_llm,
    )


if __name__ == "__main__":
    main()
