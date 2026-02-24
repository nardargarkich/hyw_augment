"""
Unified morphological analysis engine with fallback chain.

Orchestrates multiple backends (Nayiri lexicon, Apertium transducer, etc.)
behind a single interface, with TOML-based configuration.

Usage:
    from hyw_augment.engine import MorphEngine

    engine = MorphEngine.from_config()          # loads hyw_augment.toml
    results = engine.analyze("some_form")       # tries backends in order
    all_results = engine.analyze_all("form")    # returns results from every backend

    # Or build manually:
    engine = MorphEngine()
    engine.add_nayiri("data/nayiri.json", "data/words.json")
    engine.add_apertium("/path/to/apertium-hyw")
"""

from __future__ import annotations

import glob
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AnalysisResult:
    """Wrapper that tags an analysis with its source backend.

    Delegates .lemma, .pos, .description_en etc. to the inner analysis
    object (MorphAnalysis or ApertiumAnalysis — both have these attributes).
    """

    source: str  # "nayiri", "apertium", etc.
    analysis: Any  # MorphAnalysis | ApertiumAnalysis

    @property
    def lemma(self) -> str:
        return self.analysis.lemma

    @property
    def pos(self) -> str:
        return self.analysis.pos

    @property
    def description_en(self) -> str:
        return self.analysis.description_en

    @property
    def case(self) -> str | None:
        return self.analysis.case

    @property
    def number(self) -> str | None:
        return self.analysis.number

    @property
    def person(self) -> str | None:
        return self.analysis.person

    @property
    def article(self) -> str | None:
        return getattr(self.analysis, "article", None)

    def __repr__(self) -> str:
        return f"AnalysisResult({self.source}: {self.analysis!r})"


class MorphEngine:
    """Orchestrates multiple morphological backends with ordered fallback.

    Backends are tried in the order they were added.  The first backend
    that returns results wins for .analyze(); .analyze_all() queries
    every backend.
    """

    def __init__(self):
        self.backends: list[tuple[str, Any]] = []  # (name, backend)
        self.treebank = None  # Treebank | None

    # ── Construction helpers ─────────────────────────────────────────────

    def add_nayiri(self, *paths: str | Path) -> None:
        """Add a Nayiri lexicon backend (one or more JSON files, merged)."""
        from hyw_augment.nayiri import Lexicon

        resolved = _expand_paths(paths)
        if not resolved:
            return
        lex = Lexicon.from_files(*resolved)
        self.backends.append(("nayiri", lex))

    def add_apertium(self, apertium_dir: str | Path) -> None:
        """Add an Apertium transducer backend."""
        from hyw_augment.apertium import ApertiumAnalyzer

        apt = ApertiumAnalyzer(apertium_dir)
        if apt.available:
            self.backends.append(("apertium", apt))

    def load_treebank(self, *paths: str | Path) -> None:
        """Load UD treebank files."""
        from hyw_augment.conllu import Treebank

        resolved = _expand_paths(paths)
        if not resolved:
            return
        self.treebank = Treebank.from_files(*resolved)

    @classmethod
    def from_config(cls, config_path: str | Path = "hyw_augment.toml") -> MorphEngine:
        """Build a MorphEngine from a TOML config file.

        Paths in the config are resolved relative to the config file's
        directory.  Glob patterns in paths are expanded.
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")

        with config_path.open("rb") as f:
            cfg = tomllib.load(f)

        base_dir = config_path.parent
        engine = cls()

        # Nayiri
        nayiri_cfg = cfg.get("nayiri", {})
        nayiri_paths = nayiri_cfg.get("paths", [])
        if nayiri_paths:
            resolved = _resolve_config_paths(nayiri_paths, base_dir)
            if resolved:
                engine.add_nayiri(*resolved)

        # Apertium
        apt_cfg = cfg.get("apertium", {})
        apt_dir = apt_cfg.get("dir")
        if apt_dir:
            apt_path = Path(apt_dir)
            if not apt_path.is_absolute():
                apt_path = base_dir / apt_path
            engine.add_apertium(apt_path)

        # Treebank
        tb_cfg = cfg.get("treebank", {})
        tb_paths = tb_cfg.get("paths", [])
        if tb_paths:
            resolved = _resolve_config_paths(tb_paths, base_dir)
            if resolved:
                engine.load_treebank(*resolved)

        return engine

    # ── Analysis ─────────────────────────────────────────────────────────

    def analyze(self, form: str) -> list[AnalysisResult]:
        """Analyze a form using the first backend that returns results."""
        for name, backend in self.backends:
            raw = backend.analyze(form)
            if not raw and name == "nayiri":
                raw = backend.analyze_insensitive(form)
            if raw:
                return [AnalysisResult(source=name, analysis=a) for a in raw]
        return []

    def analyze_all(self, form: str) -> dict[str, list[AnalysisResult]]:
        """Analyze a form against every backend, returning all results."""
        results: dict[str, list[AnalysisResult]] = {}
        for name, backend in self.backends:
            raw = backend.analyze(form)
            if not raw and name == "nayiri":
                raw = backend.analyze_insensitive(form)
            if raw:
                results[name] = [AnalysisResult(source=name, analysis=a) for a in raw]
        return results

    def analyze_batch(
        self, forms: list[str],
    ) -> dict[str, list[AnalysisResult]]:
        """Batch-analyze forms: try Nayiri first (dict lookup), then batch
        the remaining misses through Apertium in one subprocess call."""
        results: dict[str, list[AnalysisResult]] = {}
        remaining = list(forms)

        for name, backend in self.backends:
            if not remaining:
                break

            if hasattr(backend, "analyze_batch"):
                batch = backend.analyze_batch(remaining)
                still_missing = []
                for form in remaining:
                    hits = batch.get(form, [])
                    if hits:
                        results[form] = [AnalysisResult(source=name, analysis=a) for a in hits]
                    else:
                        still_missing.append(form)
                remaining = still_missing
            else:
                still_missing = []
                for form in remaining:
                    raw = backend.analyze(form)
                    if not raw and name == "nayiri":
                        raw = backend.analyze_insensitive(form)
                    if raw:
                        results[form] = [AnalysisResult(source=name, analysis=a) for a in raw]
                    else:
                        still_missing.append(form)
                remaining = still_missing

        return results

    # ── Introspection ────────────────────────────────────────────────────

    def summary(self) -> str:
        lines = [f"MorphEngine with {len(self.backends)} backend(s):"]
        for name, backend in self.backends:
            lines.append(f"  [{name}]")
            # indent each backend's own summary
            for sub_line in backend.summary().split("\n"):
                lines.append(f"    {sub_line}")
        if self.treebank:
            lines.append(f"  [treebank]")
            for sub_line in self.treebank.summary().split("\n"):
                lines.append(f"    {sub_line}")
        return "\n".join(lines)

    def close(self) -> None:
        """Clean up backends that hold resources (e.g. Apertium subprocess)."""
        for _name, backend in self.backends:
            if hasattr(backend, "close"):
                backend.close()

    def __enter__(self) -> MorphEngine:
        return self

    def __exit__(self, *args) -> None:
        self.close()


# ── Path helpers ─────────────────────────────────────────────────────────

def _expand_paths(paths: tuple[str | Path, ...]) -> list[Path]:
    """Expand globs and return sorted list of existing Paths."""
    result = []
    for p in paths:
        p_str = str(p)
        if "*" in p_str or "?" in p_str:
            result.extend(Path(m) for m in sorted(glob.glob(p_str)))
        else:
            result.append(Path(p))
    return result


def _resolve_config_paths(raw_paths: list[str], base_dir: Path) -> list[Path]:
    """Resolve config paths relative to base_dir, expanding globs."""
    result = []
    for p in raw_paths:
        full = base_dir / p if not Path(p).is_absolute() else Path(p)
        full_str = str(full)
        if "*" in full_str or "?" in full_str:
            result.extend(Path(m) for m in sorted(glob.glob(full_str)))
        else:
            result.append(full)
    return result
