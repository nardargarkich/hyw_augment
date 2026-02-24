#!/usr/bin/env python3
"""
Western Armenian morphological toolkit CLI.

Loads backends from hyw_augment.toml by default, or override with flags:

    python -m hyw_augment.cli --analyze "WORD"
    python -m hyw_augment.cli --analyze "WORD" --config hyw_augment.toml
    python -m hyw_augment.cli --nayiri data/*.json --analyze "WORD"
    python -m hyw_augment.cli --coverage
    python -m hyw_augment.cli --coverage --mismatches data/mismatches.tsv
"""

import argparse
import sys
from pathlib import Path


def _find_default_config() -> Path | None:
    """Look for hyw_augment.toml in CWD or parent dirs."""
    candidate = Path("hyw_augment.toml")
    if candidate.exists():
        return candidate
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Western Armenian morphological toolkit"
    )
    parser.add_argument(
        "--config",
        metavar="FILE",
        help="Path to TOML config file (default: auto-detect hyw_augment.toml)",
    )
    parser.add_argument(
        "--conllu",
        nargs="+",
        help="Path(s) to .conllu treebank files (overrides config)",
    )
    parser.add_argument(
        "--nayiri",
        nargs="+",
        help="Path(s) to Nayiri lexicon JSON (overrides config)",
    )
    parser.add_argument(
        "--apertium",
        metavar="DIR",
        help="Path to apertium-hyw build directory (overrides config)",
    )
    parser.add_argument(
        "--analyze",
        help="Analyze a single word form",
    )
    parser.add_argument(
        "--generate",
        help="Generate forms for a lemma",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run coverage check (requires treebank + at least one analyzer)",
    )
    parser.add_argument(
        "--mismatches",
        metavar="FILE",
        help="Write full mismatch list to a TSV file (use with --coverage)",
    )
    args = parser.parse_args()

    # ── Build engine ─────────────────────────────────────────────────────

    from hyw_augment.engine import MorphEngine

    has_explicit_flags = args.nayiri or args.apertium or args.conllu

    if has_explicit_flags:
        # Explicit flags: build engine manually (flags override config)
        engine = MorphEngine()
        if args.nayiri:
            engine.add_nayiri(*args.nayiri)
        if args.apertium:
            engine.add_apertium(args.apertium)
        if args.conllu:
            engine.load_treebank(*args.conllu)
    else:
        # Use config file
        config_path = Path(args.config) if args.config else _find_default_config()
        if config_path is None:
            parser.error(
                "No hyw_augment.toml found and no --nayiri/--apertium/--conllu flags given.\n"
                "  Either create a config file or pass flags explicitly."
            )
        engine = MorphEngine.from_config(config_path)

    with engine:
        print(engine.summary())
        print()

        # ── Analyze ──────────────────────────────────────────────────────

        if args.analyze:
            all_results = engine.analyze_all(args.analyze)
            if all_results:
                for source, results in all_results.items():
                    print(f"═══ Analysis of '{args.analyze}' ({source}) ═══")
                    for r in results:
                        print(f"  {r.lemma} [{r.pos}] — {r.description_en}")
            else:
                backends = ", ".join(name for name, _ in engine.backends) or "none loaded"
                print(f"'{args.analyze}' not found (backends: {backends})")
            print()

        # ── Generate ─────────────────────────────────────────────────────

        if args.generate:
            # Generation is Nayiri-specific for now (uses its inflection system)
            nayiri_backend = None
            for name, backend in engine.backends:
                if name == "nayiri":
                    nayiri_backend = backend
                    break

            if nayiri_backend:
                forms = nayiri_backend.generate(args.generate)
                if forms:
                    print(f"═══ Forms of '{args.generate}' (Nayiri) ═══")
                    seen = set()
                    for surface, inf in forms:
                        key = (surface, inf.display_name_en)
                        if key not in seen:
                            seen.add(key)
                            print(f"  {surface:30s}  {inf.display_name_en}")
                else:
                    print(f"Lemma '{args.generate}' not found in Nayiri lexicon.")
            else:
                print("Generation requires Nayiri lexicon (not loaded).")
            print()

        # ── Coverage ─────────────────────────────────────────────────────

        if args.coverage:
            nayiri_backend = None
            apertium_backend = None
            for name, backend in engine.backends:
                if name == "nayiri":
                    nayiri_backend = backend
                elif name == "apertium":
                    apertium_backend = backend

            if engine.treebank is None or nayiri_backend is None:
                print(
                    "ERROR: --coverage requires treebank and Nayiri lexicon",
                    file=sys.stderr,
                )
                sys.exit(1)

            from hyw_augment.coverage import check_coverage

            report = check_coverage(
                engine.treebank, nayiri_backend, apertium=apertium_backend,
            )
            print(report.summary())
            if args.mismatches:
                report.write_mismatches(Path(args.mismatches))
                print(f"\nMismatches written to {args.mismatches}")


if __name__ == "__main__":
    main()
