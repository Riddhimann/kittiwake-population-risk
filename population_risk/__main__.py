import argparse

from .pipeline import run


def main():
    parser = argparse.ArgumentParser(description="Rebuild the kittiwake population-risk study.")
    parser.add_argument("--data", default="data/kittiwake_gpdd_6633.xlsx")
    parser.add_argument("--output", default="artifacts")
    parser.add_argument("--simulations", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    run(args.data, args.output, args.simulations, args.seed)


if __name__ == "__main__":
    main()

