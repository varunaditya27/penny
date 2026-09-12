import argparse
import csv
import logging
import os
import sys

cur_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(cur_dir)
while cur_dir in sys.path:
    sys.path.remove(cur_dir)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from typing import List, Optional
from dotenv import load_dotenv

# Automatically load environment variables (such as GROQ_API_KEY) from .env in repo root
load_dotenv()

from code.data.evidence import EvidenceManager, tracker
from code.data.loader import DataLoader
from code.evaluation.evaluator import Evaluator
from code.models.results import OutputRow
from code.pipeline import DecisionPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("buy_or_wait.main")


def run_pipeline(
    sample_mode: bool = False,
    output_path: Optional[str] = None,
    tolerance: float = 5.0,
    use_llm: Optional[bool] = None,
) -> None:
    if output_path is None:
        output_path = "evaluation/sample_output.csv" if sample_mode else "output.csv"

    if use_llm is None:
        use_llm = not sample_mode

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

    # Write output to CSV
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

    # Write to root output.csv
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for r in output_rows:
            writer.writerow(r.to_csv_row())
    logger.info(f"Successfully wrote {len(output_rows)} rows to {output_path}")

    # Also write to dataset/output.csv per challenge contract in production mode
    if not sample_mode:
        dataset_output_path = os.path.join("dataset", "output.csv")
        with open(dataset_output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(fieldnames)
            for r in output_rows:
                writer.writerow(r.to_csv_row())
        logger.info(f"Successfully synchronized {len(output_rows)} rows to {dataset_output_path}")

    # If in sample mode, evaluate against ground truth
    if sample_mode:
        with open("dataset/sample_requests.csv", "r", encoding="utf-8") as f:
            ground_truth = list(csv.DictReader(f))
        report = Evaluator.evaluate(dict_rows, ground_truth, safe_amount_tolerance=tolerance)
        report.print_summary()

    # Generate token usage report
    report_content = tracker.generate_report_markdown(total_requests=len(requests))
    os.makedirs("evaluation", exist_ok=True)
    usage_filename = "sample_usage_report.md" if sample_mode else "usage_report.md"
    usage_path = os.path.join("evaluation", usage_filename)
    with open(usage_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    logger.info(f"Updated usage report at {usage_path}")


def main():
    parser = argparse.ArgumentParser(description="Buy or Wait? AI-powered financial decision agent CLI.")
    parser.add_argument("--eval-sample", action="store_true", help="Run evaluation on dataset/sample_requests.csv")
    parser.add_argument("--tolerance", type=float, default=5.0, help="Numerical tolerance for safe amount")
    parser.add_argument("--output", type=str, default=None, help="Path to write output CSV")
    parser.add_argument("--use-llm", action="store_true", help="Explicitly enable LLM explanation calls via Groq API")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM calls and use deterministic templates only")
    args = parser.parse_args()

    use_llm = None
    if args.no_llm:
        use_llm = False
    elif args.use_llm:
        use_llm = True

    run_pipeline(
        sample_mode=args.eval_sample,
        output_path=args.output,
        tolerance=args.tolerance,
        use_llm=use_llm,
    )


if __name__ == "__main__":
    main()
