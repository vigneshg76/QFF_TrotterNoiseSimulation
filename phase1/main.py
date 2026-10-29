"""End-to-end PS-S3 benchmark.   python main.py            (full run)
                                 python main.py --quick     (fast smoke test, ~1 minute)"""
import argparse

from src.experiment import run_all
from src.visualization import make_all_figures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="reduced grid for a smoke test")
    args = ap.parse_args()
    df, store = run_all(quick=args.quick)
    make_all_figures(df, store)
    print("\nDone. Tables -> results/tables/, figures -> results/figures/, versions -> results/environment.json")


if __name__ == "__main__":
    main()
