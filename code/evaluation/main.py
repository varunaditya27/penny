import argparse
import sys

from code.evaluation.evaluator import Evaluator


def main():
    parser = argparse.ArgumentParser(description="Evaluate predictions against ground truth.")
    parser.add_argument("--pred", type=str, default="output.csv", help="Path to predictions CSV")
    parser.add_argument("--truth", type=str, default="dataset/sample_requests.csv", help="Path to ground truth CSV")
    parser.add_argument("--tolerance", type=float, default=1.0, help="Numerical tolerance for safe amount")
    args = parser.parse_args()

    try:
        report = Evaluator.evaluate_csv_files(args.pred, args.truth, tolerance=args.tolerance)
        report.print_summary()
        if report.overall_accuracy < 100.0:
            sys.exit(1)
        sys.exit(0)
    except Exception as e:
        print(f"Error during evaluation: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
