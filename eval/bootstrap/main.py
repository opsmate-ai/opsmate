import argparse

from eval.bootstrap.bootstrap import bootstrap, verify_issues


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()
    print(f"Bootstrapping {args.count} issues")
    bootstrap(count=args.count)
    verify_issues()
