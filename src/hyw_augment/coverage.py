"""
Cross-reference the UD treebank against the Nayiri lexicon to measure coverage.

This tells us:
- What % of treebank tokens can be found in the lexicon
- Which tokens are missing (gaps in lexicon coverage)
- Where lemma mappings agree or disagree between the two resources
- POS-level breakdown of coverage

Usage:
    from hyw_augment import Treebank, Lexicon, check_coverage

    tb = Treebank.from_file("data/hyw_armtdp-ud-dev.conllu")
    lex = Lexicon.from_file("data/nayiri-armenian-lexicon.json")
    report = check_coverage(tb, lex)
    print(report.summary())
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter

from hyw_augment.conllu import Treebank, Token
from hyw_augment.nayiri import Lexicon


# POS tags we don't expect the lexicon to cover
SKIP_POS = {"PUNCT", "NUM", "SYM", "X"}


@dataclass
class TokenMatch:
    """Result of checking one UD token against the lexicon."""

    token: Token
    found: bool  # surface form found in lexicon
    lemma_match: bool  # at least one analysis shares the UD lemma
    analyses_count: int  # how many analyses the lexicon returned
    pos_match: bool  # at least one analysis shares the UD POS


@dataclass
class CoverageReport:
    """Aggregated coverage statistics."""

    total_tokens: int = 0
    skipped_tokens: int = 0  # PUNCT etc.
    checked_tokens: int = 0
    found_tokens: int = 0
    lemma_matches: int = 0
    pos_matches: int = 0

    # Breakdown by UD POS
    by_pos: dict[str, dict[str, int]] = field(default_factory=dict)

    # Interesting cases
    missing_forms: Counter = field(default_factory=Counter)  # form → count
    missing_lemmas: Counter = field(default_factory=Counter)  # lemma → count
    lemma_mismatches: list[tuple[str, str, str, list[str]]] = field(
        default_factory=list
    )  # (form, ud_lemma, ud_pos, [nayiri_lemmas])

    def summary(self) -> str:
        if self.checked_tokens == 0:
            return "No tokens checked."

        pct = lambda n, d: f"{100*n/d:.1f}%" if d > 0 else "N/A"

        lines = [
            "═══ Coverage Report ═══",
            "",
            f"Total tokens:   {self.total_tokens}",
            f"Skipped (PUNCT etc.): {self.skipped_tokens}",
            f"Checked:        {self.checked_tokens}",
            "",
            f"Found in lexicon:    {self.found_tokens:5d}  ({pct(self.found_tokens, self.checked_tokens)})",
            f"  Lemma also matches:  {self.lemma_matches:5d}  ({pct(self.lemma_matches, self.checked_tokens)})",
            f"  POS also matches:    {self.pos_matches:5d}  ({pct(self.pos_matches, self.checked_tokens)})",
            f"Not found:           {self.checked_tokens - self.found_tokens:5d}  ({pct(self.checked_tokens - self.found_tokens, self.checked_tokens)})",
            "",
            "─── By POS ───",
        ]

        for pos in sorted(self.by_pos.keys()):
            stats = self.by_pos[pos]
            checked = stats.get("checked", 0)
            found = stats.get("found", 0)
            lines.append(
                f"  {pos:12s}  {found:4d}/{checked:4d}  ({pct(found, checked)})"
            )

        lines.append("")
        lines.append("─── Top 20 missing forms ───")
        for form, count in self.missing_forms.most_common(20):
            lines.append(f"  {form:25s}  ×{count}")

        lines.append("")
        lines.append("─── Top 20 missing lemmas ───")
        for lemma, count in self.missing_lemmas.most_common(20):
            lines.append(f"  {lemma:25s}  ×{count}")

        if self.lemma_mismatches:
            lines.append("")
            lines.append("─── Sample lemma mismatches (form found, lemma disagrees) ───")
            for form, ud_lemma, ud_pos, nayiri_lemmas in self.lemma_mismatches[:15]:
                nl = ", ".join(nayiri_lemmas[:3])
                lines.append(
                    f"  {form:20s}  UD: {ud_lemma:15s} ({ud_pos})  Nayiri: {nl}"
                )

        return "\n".join(lines)


# Map Nayiri POS names to UD POS tags for comparison
_NAYIRI_TO_UD_POS = {
    "NOUN": "NOUN",
    "VERB": "VERB",
    "ADJECTIVE": "ADJ",
    "ADVERB": "ADV",
}


def check_coverage(
    treebank: Treebank,
    lexicon: Lexicon,
    *,
    skip_pos: set[str] | None = None,
) -> CoverageReport:
    """
    Check how many treebank tokens the lexicon can analyze.

    Args:
        treebank: Parsed UD treebank
        lexicon: Loaded Nayiri lexicon
        skip_pos: POS tags to skip (default: PUNCT, NUM, SYM, X)
    """
    if skip_pos is None:
        skip_pos = SKIP_POS

    report = CoverageReport()

    for sent in treebank:
        for tok in sent.real_tokens:
            report.total_tokens += 1

            if tok.upos in skip_pos:
                report.skipped_tokens += 1
                continue

            report.checked_tokens += 1

            # Per-POS tracking
            pos_stats = report.by_pos.setdefault(tok.upos, {"checked": 0, "found": 0})
            pos_stats["checked"] += 1

            # Try to find the surface form in the lexicon
            analyses = lexicon.analyze(tok.form)
            if not analyses:
                # Try case-insensitive (handles sentence-initial caps)
                analyses = lexicon.analyze_insensitive(tok.form)

            if analyses:
                report.found_tokens += 1
                pos_stats["found"] += 1

                # Check lemma agreement
                nayiri_lemmas = list({a.lemma for a in analyses})
                if tok.lemma in nayiri_lemmas:
                    report.lemma_matches += 1
                else:
                    report.lemma_mismatches.append(
                        (tok.form, tok.lemma, tok.upos, nayiri_lemmas)
                    )

                # Check POS agreement
                nayiri_pos_ud = {
                    _NAYIRI_TO_UD_POS.get(a.pos, a.pos) for a in analyses
                }
                if tok.upos in nayiri_pos_ud:
                    report.pos_matches += 1
            else:
                report.missing_forms[tok.form] += 1
                report.missing_lemmas[tok.lemma] += 1

    return report
