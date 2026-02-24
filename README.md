# hyw_augment

## Project to augment LLMs for better Western Armenian language parsing

## WARNING! Still very much in development, many known issues

## What this is

A morphological augmentation layer for Western Armenian (hyw) LLMs. The goal is
to improve LLM output quality in Western Armenian by giving the model access to
structured linguistic data at inference time, rather than fine-tuning. (Fine tuning may come later.)

This is **model-agnostic** — it sits between the user and any LLM (currently
targeting Ministral 14B via Ollama, but portable to anything).

## Why

- No conversational Western Armenian LLM exists yet
- Eastern Armenian has [HyGPT](https://huggingface.co/Gen2B/HyGPT-10b) and [ArmenianGPT](https://huggingface.co/ArmGPT/ArmenianGPT-0.1-12B); Western has nothing; even given that it should be easier to get an Eastern Armenian-speaking LLM to figure out Western Armenian, it would be nice to get up and running with higher-parameter models
- The NLP infrastructure has a lot of parts already built (UD treebank, Nayiri lexicon, DALiH project, Apertium Western Armenian Transducer) but it's not currently connected to conversational generation
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
- Released 2026-02-15 (new!)
- 7,076 lexemes, 7,931 lemmas, 1,491,045 word forms, 709 inflections
- Western Armenian traditional orthography only (this release)
- JSON format, hierarchical: lexeme → lemma → word forms → inflection IDs
- License: CC BY 4.0
- Key person: Serouj Ourishian

### Apertium Western Armenian Transducer

* Source: https://github.com/apertium/apertium-hyw
* A full morphological transducer with 75K lemma lexicon, ~90%+ naive coverage
* Handles inflectional morphology and some productive derivation
* Built with HFST/lexd/twol, GPL-3.0
* Key people: Hossep Dolatian (Stony Brook University), Daniel Swanson (Indiana University), Jonathan Washington (Swarthmore College)
* Paper: Dolatian et al. (2022), "A Free/Open-Source Morphological Transducer for Western Armenian" — presented at DigitAm @LREC 2022
* Integrated as fallback analyzer backend alongside Nayiri lexicon (configured in `hyw_augment.toml`)

## Architecture

```
src/hyw_augment/
├── __init__.py               # Package exports
├── __main__.py               # python -m hyw_augment
├── cli.py                    # CLI runner (uses MorphEngine)
├── engine.py                 # MorphEngine — unified backend orchestration + config
├── conllu.py                 # CoNLL-U treebank parser
├── nayiri.py                 # Nayiri lexicon parser + morphological lookup
├── apertium.py               # Apertium transducer wrapper (persistent hfst-lookup)
├── derivation.py             # Derivational morphology (prefix/suffix stripping) [WIP]
├── extract_words_from_UD.py  # extracts unmatched words from UD in Nayiri format
└── coverage.py               # Cross-reference treebank ↔ lexicon

hyw_augment.toml              # Default config (paths to data, backends)
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

### apertium.py
- `ApertiumAnalyzer(apertium_dir)` — wraps `hfst-lookup` with the compiled transducer
- `apt.analyze("form")` → list of ApertiumAnalysis (form → lemma + apertium tags)
- `apt.analyze_batch(["form1", "form2", ...])` → dict of form → analyses (single subprocess call)
- `apt.generate("lemma", ["n", "pl", "abl", "def"])` → list of surface forms
- `ApertiumAnalysis` is duck-type compatible with `MorphAnalysis` (.lemma, .pos, .description_en, .case, .number, etc.)
- Apertium tag set mapped to human-readable labels and to Nayiri/UD-compatible feature names

### engine.py
- `MorphEngine.from_config("hyw_augment.toml")` — loads everything from config
- `engine.analyze("form")` → list of AnalysisResult (first backend that hits)
- `engine.analyze_all("form")` → dict of backend name → results (every backend)
- `engine.analyze_batch(forms)` → efficient bulk analysis with automatic fallback
- `AnalysisResult` wraps any backend's analysis with `.source` tag + delegates `.lemma`, `.pos`, etc.

### coverage.py
- `check_coverage(treebank, lexicon, apertium=apt)` → CoverageReport
- Nayiri first pass, then batches all misses through Apertium in one call
- Reports: Nayiri found / Apertium rescued / still missing, per-POS breakdown, lemma + POS agreement

## Usage

### Config

Create `hyw_augment.toml` in the project root (one is included):
```toml
[nayiri]
paths = ["data/nayiri-armenian-lexicon-2026-02-15-v1.json", "data/extracted-words.json"]

[apertium]
dir = "/path/to/apertium-hyw"

[treebank]
paths = ["data/hyw_armtdp-ud-train.conllu", "data/hyw_armtdp-ud-dev.conllu", "data/hyw_armtdp-ud-test.conllu"]
```

With a config file present, the CLI loads everything automatically — no flags needed.

### CLI

Analyze a word (uses all configured backends):
`python -m hyw_augment.cli --analyze "WORD"`

Generate forms from a lemma:
`python -m hyw_augment.cli --generate "LEMMA"`

Coverage check:
`python -m hyw_augment.cli --coverage`

Coverage with mismatch export:
`python -m hyw_augment.cli --coverage --mismatches data/mismatches.tsv`

Override config with explicit flags:
`python -m hyw_augment.cli --nayiri data/*.json --apertium /path/to/apertium-hyw --analyze "WORD"`

Extract mismatched words between UD and Nayiri (first pass for building function words list):
```
python -m hyw_augment.extract_words_from_UD \
    --conllu data/*.conllu \
    --nayiri data/nayiri-armenian-lexicon-2026-02-15-v1.json \
    --output data/extracted-words.json \
    --indent \
    --min-freq 3 # can adapt up or down
```

### Apertium transducer setup

For expanded morphological coverage, install the Apertium Western Armenian transducer:

1. Install system packages: `hfst`, `lttoolbox`, `apertium`, `vislcg3`
2. Clone and build `lexd` : https://github.com/apertium/lexd
3. Clone and build: https://github.com/apertium/apertium-hyw
4. Set the `dir` in `hyw_augment.toml` under `[apertium]`

### Python

```python
from hyw_augment import MorphEngine

# Load from config
engine = MorphEngine.from_config()

# Analyze — first backend that hits
results = engine.analyze("WORD")
for r in results:
    print(r.source, r.lemma, r.pos, r.description_en)

# Compare all backends
all_results = engine.analyze_all("WORD")
for source, results in all_results.items():
    print(f"--- {source} ---")
    for r in results:
        print(f"  {r.lemma} [{r.pos}]")

# Treebank exploration
from hyw_augment import Treebank
tb = Treebank.from_dir("data/")
tb.vocab()                        # lemma -> set of observed surface forms
tb.pos_distribution()
tb.deprel_distribution()
```


## Current questions

- What sort of word is է and similar? An auxilary? A function word? A suffix? It is obviously all of these, but how best to integrate? Need to make list of function words separate from words missing from Nayiri lexicon in general (lexicon is stated on project page to be incomplete/rolling release).
- Somewhat similarly: currently this is working on inflectional morphology, ie we're taking lemmas and giving them word forms. But Armenian is (at least somewhat) agglutinative. How to handle derivational morphology (ie building words from word-bits)? For example, in present setup from Nayiri, "անհատ" is one lexeme/lemma; but it's also ան = without հատ = one discrete unit, and native speakers would recognize this pattern. A parser should too, and this does not. Quick'n'dirty step one is to do stripping based on set prefix/suffix list: need to make. And then rules for how the words sometimes change when these attach. Future steps may lead towards a cleaner, more built out finite state transducer.


## Grab-bag of small(er) TODOs/stretch goals/related project ideas:

  - clean up code
  - find/make/grab more texts, especially colloquial ones
  - create minimap of different latinizations
  - use actual branches instead of doing active development inside of main (sorry -- wanted to get this off the ground fast, and show work to anyone interested!)