# hyw-augment — Project Notes

## What this is

A morphological augmentation layer for Western Armenian (hyw) LLMs. The goal is
to improve LLM output quality in Western Armenian by giving the model access to
structured linguistic data at inference time, rather than fine-tuning.

This is **model-agnostic** — it sits between the user and any LLM (currently
targeting Ministral 14B via Ollama, but portable to anything).

## Why

- No conversational Western Armenian LLM exists yet
- Eastern Armenian has HyGPT and ArmenianGPT; Western has nothing
- The NLP infrastructure is arriving (UD treebank, Nayiri lexicon, DALiH project)
  but nobody has connected it to conversational generation
- Fine-tuning a 14B model in a week on limited data isn't realistic
- An augmentation layer is portable between models and immediately useful

## Data sources

### UD Western Armenian ArmTDP treebank
- Source: https://github.com/UniversalDependencies/UD_Western_Armenian-ArmTDP
- 6,656 sentences, ~122K tokens in CoNLL-U format
- Full dependency trees, POS tags, morphological features, lemmas
- All manually verified — the only such corpus for Western Armenian
- License: CC BY-SA 4.0
- Key person: Marat M. Yavrumyan (Yerevan State University)

### Nayiri Armenian Lexicon
- Source: http://www.nayiri.com/nayiri-armenian-lexicon?l=en
- Released 2026-02-15 (brand new!)
- 7,076 lexemes, 7,931 lemmas, 1,491,045 word forms, 709 inflections
- Western Armenian traditional orthography only (this release)
- JSON format, hierarchical: lexeme → lemma → word forms → inflection IDs
- License: CC BY 4.0
- Key person: Serouj Ourishian

## Architecture

```
src/hyw_augment/
├── __init__.py      # Package exports
├── __main__.py      # python -m hyw_augment
├── cli.py           # CLI runner
├── conllu.py        # CoNLL-U treebank parser
├── nayiri.py        # Nayiri lexicon parser + morphological lookup
└── coverage.py      # Cross-reference treebank ↔ lexicon
```

### conllu.py
- `Treebank.from_file()` / `.from_files()` / `.from_dir()`
- `Sentence` with `.tokens`, `.real_tokens`, `.text`, `.root()`
- `Token` with `.form`, `.lemma`, `.upos`, `.feats`, `.deprel`, etc.
- Vocab/distribution helpers

### nayiri.py
- `Lexicon.from_file()` — loads JSON, builds indexes
- `lex.analyze("form")` → list of MorphAnalysis (form → lemma + features)
- `lex.generate("lemma", case=..., number=...)` → list of surface forms
- `lex.is_valid_form("form")` → bool

### coverage.py
- `check_coverage(treebank, lexicon)` → CoverageReport
- Reports: % found, lemma agreement, POS agreement, missing forms

## Next steps

1. **Run coverage check** with full data (all 3 UD splits + full Nayiri JSON)
2. **Build feature mapping** between UD tags and Nayiri inflection categories
3. **Extract syntactic templates** from UD treebank — common sentence patterns
4. **Ollama integration** — wrap Ministral with morphological validation
5. **Prompt engineering** — system prompts that leverage the linguistic data

## Conference context

Presenting at "It Takes a Diaspora to Raise a Language" at USC, Feb 27–March 1.
Panel: "Armenian Language in the Era of Artificial Intelligence"
Key panelists to be aware of:
- Victoria Khurshudyan (DALiH project lead, used same UD data for PIE models)
- Chahan Vidal-Gorène (Calfa, co-author on cross-dialectal transfer paper)
- Artur Ishkhanyan (algorithmic sovereignty / ethics angle)
- Vicken Asadourian (Arshaluys platform for diaspora revitalization)

Our angle: bridging the gap between NLP infrastructure and actual conversation.
Running locally, open-source, privacy-first — aligns with sovereignty concerns.
