"""
Parse CoNLL-U files from the UD Western Armenian ArmTDP treebank.

Usage:
    from hyw_augment.conllu import Treebank

    tb = Treebank.from_file("data/hyw_armtdp-ud-train.conllu")
    print(f"{len(tb)} sentences, {tb.token_count} tokens")

    for sent in tb:
        for tok in sent.tokens:
            print(tok.form, tok.lemma, tok.upos, tok.feats)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass(slots=True)
class Token:
    """A single token in a CoNLL-U sentence."""

    id: str  # usually "1", "2", etc. Can be "1-2" for MWTs
    form: str  # surface form as it appears in text
    lemma: str  # dictionary form
    upos: str  # universal POS tag (NOUN, VERB, ADJ, ...)
    xpos: str  # language-specific POS (unused in ArmTDP, always "_")
    feats: dict[str, str]  # morphological features
    head: str  # id of syntactic head ("0" for root)
    deprel: str  # dependency relation (nsubj, obj, amod, ...)
    deps: str  # enhanced dependencies (unused in ArmTDP)
    misc: dict[str, str]  # SpaceAfter, Translit, LTranslit, etc.

    @property
    def is_multiword(self) -> bool:
        """True for multiword token range lines like '1-2'."""
        return "-" in self.id

    @property
    def is_empty(self) -> bool:
        """True for empty nodes like '1.1' (not present in ArmTDP)."""
        return "." in self.id

    @property
    def translit(self) -> str | None:
        """ISO 9985 transliteration of the form, if present."""
        return self.misc.get("Translit")

    @property
    def lemma_translit(self) -> str | None:
        """ISO 9985 transliteration of the lemma, if present."""
        return self.misc.get("LTranslit")

    @property
    def space_after(self) -> bool:
        """Whether there's a space after this token (default True)."""
        return self.misc.get("SpaceAfter") != "No"

    def feat(self, key: str) -> str | None:
        """Get a single morphological feature value."""
        return self.feats.get(key)


@dataclass
class Sentence:
    """A single sentence from the treebank."""

    tokens: list[Token] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def sent_id(self) -> str | None:
        return self.metadata.get("sent_id")

    @property
    def text(self) -> str | None:
        return self.metadata.get("text")

    @property
    def doc_title(self) -> str | None:
        return self.metadata.get("doc_title")

    @property
    def real_tokens(self) -> list[Token]:
        """Tokens excluding multiword ranges and empty nodes."""
        return [t for t in self.tokens if not t.is_multiword and not t.is_empty]

    @property
    def words(self) -> list[str]:
        """Just the surface forms."""
        return [t.form for t in self.real_tokens]

    @property
    def lemmas(self) -> list[str]:
        """Just the lemma forms."""
        return [t.lemma for t in self.real_tokens]

    def by_upos(self, *tags: str) -> list[Token]:
        """Filter real tokens by POS tag(s)."""
        tag_set = set(tags)
        return [t for t in self.real_tokens if t.upos in tag_set]

    def root(self) -> Token | None:
        """The syntactic root token."""
        for t in self.real_tokens:
            if t.deprel == "root":
                return t
        return None


class Treebank:
    """Collection of sentences parsed from CoNLL-U files."""

    def __init__(self, sentences: list[Sentence] | None = None):
        self.sentences: list[Sentence] = sentences or []

    @classmethod
    def from_file(cls, path: str | Path) -> Treebank:
        """Parse a single .conllu file."""
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        return cls(_parse_conllu(text))

    @classmethod
    def from_files(cls, *paths: str | Path) -> Treebank:
        """Parse multiple .conllu files (train + dev + test)."""
        sentences = []
        for p in paths:
            p = Path(p)
            text = p.read_text(encoding="utf-8")
            sentences.extend(_parse_conllu(text))
        return cls(sentences)

    @classmethod
    def from_dir(cls, directory: str | Path) -> Treebank:
        """Parse all .conllu files in a directory."""
        directory = Path(directory)
        paths = sorted(directory.glob("*.conllu"))
        return cls.from_files(*paths)

    def __len__(self) -> int:
        return len(self.sentences)

    def __iter__(self) -> Iterator[Sentence]:
        return iter(self.sentences)

    def __getitem__(self, idx: int) -> Sentence:
        return self.sentences[idx]

    @property
    def token_count(self) -> int:
        """Total real tokens across all sentences."""
        return sum(len(s.real_tokens) for s in self.sentences)

    def all_tokens(self) -> Iterator[Token]:
        """Iterate over all real tokens in all sentences."""
        for sent in self.sentences:
            yield from sent.real_tokens

    def unique_lemmas(self) -> set[str]:
        """Set of all distinct lemmas."""
        return {t.lemma for t in self.all_tokens()}

    def unique_forms(self) -> set[str]:
        """Set of all distinct surface forms."""
        return {t.form for t in self.all_tokens()}

    def vocab(self) -> dict[str, set[str]]:
        """Map of lemma → set of observed surface forms."""
        result: dict[str, set[str]] = {}
        for t in self.all_tokens():
            result.setdefault(t.lemma, set()).add(t.form)
        return result

    def pos_distribution(self) -> dict[str, int]:
        """Count tokens by POS tag."""
        counts: dict[str, int] = {}
        for t in self.all_tokens():
            counts[t.upos] = counts.get(t.upos, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def deprel_distribution(self) -> dict[str, int]:
        """Count dependency relation types."""
        counts: dict[str, int] = {}
        for t in self.all_tokens():
            counts[t.deprel] = counts.get(t.deprel, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def summary(self) -> str:
        """Quick summary stats."""
        lines = [
            f"Sentences:      {len(self)}",
            f"Tokens:         {self.token_count}",
            f"Unique forms:   {len(self.unique_forms())}",
            f"Unique lemmas:  {len(self.unique_lemmas())}",
            f"POS tags:       {len(self.pos_distribution())}",
            "",
            "POS distribution:",
        ]
        for pos, count in self.pos_distribution().items():
            lines.append(f"  {pos:12s} {count:6d}")
        return "\n".join(lines)


# ── Internal parsing ──────────────────────────────────────────────────────────


def _parse_feats(raw: str) -> dict[str, str]:
    """Parse 'Case=Nom|Number=Sing' → {'Case': 'Nom', 'Number': 'Sing'}."""
    if raw == "_":
        return {}
    result = {}
    for pair in raw.split("|"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k] = v
    return result


def _parse_misc(raw: str) -> dict[str, str]:
    """Parse misc column: 'SpaceAfter=No|Translit=x' → dict."""
    if raw == "_":
        return {}
    result = {}
    for pair in raw.split("|"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k] = v
        else:
            # bare flag like "SpaceAfter"
            result[pair] = ""
    return result


def _parse_conllu(text: str) -> list[Sentence]:
    """Parse raw CoNLL-U text into Sentence objects."""
    sentences: list[Sentence] = []
    current = Sentence()

    for line in text.split("\n"):
        line = line.rstrip()

        if not line:
            # blank line = sentence boundary
            if current.tokens or current.metadata:
                sentences.append(current)
                current = Sentence()
            continue

        if line.startswith("#"):
            # comment / metadata line
            m = re.match(r"#\s*(\S+)\s*=\s*(.*)", line)
            if m:
                current.metadata[m.group(1)] = m.group(2).strip()
            continue

        # token line: 10 tab-separated fields
        fields = line.split("\t")
        if len(fields) != 10:
            continue

        tok = Token(
            id=fields[0],
            form=fields[1],
            lemma=fields[2],
            upos=fields[3],
            xpos=fields[4],
            feats=_parse_feats(fields[5]),
            head=fields[6],
            deprel=fields[7],
            deps=fields[8],
            misc=_parse_misc(fields[9]),
        )
        current.tokens.append(tok)

    # don't lose the last sentence if file doesn't end with blank line
    if current.tokens or current.metadata:
        sentences.append(current)

    return sentences
