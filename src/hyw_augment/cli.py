#!/usr/bin/env python3
"""
Quick-start script. Run from the project root:

    python -m hyw_augment.cli --conllu data/hyw_armtdp-ud-dev.conllu \
                              --nayiri data/nayiri-armenian-lexicon.json

Or just one at a time:

    python -m hyw_augment.cli --conllu data/hyw_armtdp-ud-dev.conllu
    python -m hyw_augment.cli --nayiri data/nayiri-armenian-lexicon-sample.json
    python -m hyw_augment.cli --conllu data/*.conllu --nayiri data/nayiri*.json
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Western Armenian morphological toolkit"
    )
    parser.add_argument(
        "--conllu",
        nargs="+",
        help="Path(s) to .conllu treebank files",
    )
    parser.add_argument(
        "--nayiri",
        nargs="+",
        help="Path(s) to Nayiri lexicon JSON",
    )
    parser.add_argument(
        "--analyze",
        help="Analyze a single word form against the lexicon",
    )
    parser.add_argument(
        "--generate",
        help="Generate forms for a lemma",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run coverage check (requires both --conllu and --nayiri)",
    )
    args = parser.parse_args()

    tb = None
    lex = None

    # Load treebank
    if args.conllu:
        from hyw_augment.conllu import Treebank

        paths = [Path(p) for p in args.conllu]
        tb = Treebank.from_files(*paths)
        print("═══ Treebank ═══")
        print(tb.summary())
        print()

    # Load lexicon
    if args.nayiri:
        from hyw_augment.nayiri import Lexicon

        paths = [Path(p) for p in args.nayiri]
        lex = Lexicon.from_files(*paths)
        print("═══ Nayiri Lexicon ═══")
        print(lex.summary())
        print()

    # Analyze a word
    if args.analyze and lex:
        analyses = lex.analyze(args.analyze)
        if not analyses:
            analyses = lex.analyze_insensitive(args.analyze)
        if analyses:
            print(f"═══ Analysis of '{args.analyze}' ═══")
            for a in analyses:
                print(f"  {a.lemma} [{a.pos}] — {a.description_en}")
        else:
            print(f"'{args.analyze}' not found in lexicon.")
        print()

    # Generate forms
    if args.generate and lex:
        forms = lex.generate(args.generate)
        if forms:
            print(f"═══ Forms of '{args.generate}' ═══")
            seen = set()
            for surface, inf in forms:
                key = (surface, inf.display_name_en)
                if key not in seen:
                    seen.add(key)
                    print(f"  {surface:30s}  {inf.display_name_en}")
        else:
            print(f"Lemma '{args.generate}' not found in lexicon.")
        print()

    # Coverage check
    if args.coverage:
        if tb is None or lex is None:
            print("ERROR: --coverage requires both --conllu and --nayiri", file=sys.stderr)
            sys.exit(1)
        from hyw_augment.coverage import check_coverage

        report = check_coverage(tb, lex)
        print(report.summary())


if __name__ == "__main__":
    main()
