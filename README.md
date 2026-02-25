# hyw_augment

## Project to wire together Western Armenian NLP tools for better language processing 

## WARNING! Still very much in development, many known (and unknown!) issues

## What this is

A morphological augmentation layer for Western Armenian (hyw) — originally targeting LLMs, probably useful for analysis generally. The goal the project started with was/is to improve LLM output quality in Western Armenian by giving the model access to structured linguistic data at inference time, rather than fine-tuning. (Fine tuning may come later.)

This is **model-agnostic**, including human-as-"model" — it sits between a regular user and any LLM or other more in-depth machine tool.

## Why

- The NLP infrastructure has a lot of parts already built (UD treebank, Nayiri Lexicon, DALiH project, Apertium Western Armenian Transducer, Nayiri Codex) but it's not currently connected

- An augmentation layer is portable between paradigms and immediately useful

- With regard to LLMs specifically, no conversational Western Armenian LLM exists yet, and it could be useful to supplement other language resources

- Eastern Armenian has [HyGPT](https://huggingface.co/Gen2B/HyGPT-10b) and [ArmenianGPT](https://huggingface.co/ArmGPT/ArmenianGPT-0.1-12B); training on Western Corpus will take time; even given that it should be easier to get an Eastern Armenian-speaking LLM to figure out Western Armenian, it would be nice to get up and running with higher-parameter models

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

### HySpell Armenian Spell Checker

* Source: https://github.com/hyspell/HySpell_3.0.1
* Hunspell dictionary for Armenian: 160K stems, ~200 affix rules, 126 replacement/suggestion rules
* Separate dictionaries for Classical (Western) and Reformed (Eastern) orthography
* Includes Reformed↔Classical orthography conversion maps (160K word-level mappings + suffix rules)
* Includes SmallArmDic: 19K-entry Armenian explanatory dictionary with POS and definitions
* License: MIT
* Key person: Haro Mherian, Ph.D.
* Integrated for spell checking, orthography conversion, and glossary lookup (configured in `hyw_augment.toml`)

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
├── spelling.py               # Hunspell spell checker wrapper (persistent hunspell pipe)
├── orthography.py            # Reformed ↔ Classical orthography conversion
├── glossary.py               # Armenian explanatory dictionary (SmallArmDic)
├── derivation.py             # Derivational morphology (prefix/suffix stripping) [WIP]
├── extract_words_from_UD.py  # extracts unmatched words from UD in Nayiri format (potentially now unnecessary, or just duplicative)
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

### spelling.py
- `SpellChecker(dict_dir)` — wraps the `hunspell` CLI in persistent pipe mode (same pattern as Apertium)
- `sc.check("form")` → bool (is this a valid word?)
- `sc.suggest("form")` → list of suggested corrections
- `sc.check_and_suggest("form")` → (bool, list) combined check + suggest
- `sc.check_batch(forms)` / `sc.suggest_batch(forms)` → batch operations
- Uses HySpell's Classical Armenian dictionary (hy-c.aff + hy-c.dic, 160K stems)

### orthography.py
- `OrthographyConverter(dict_dir)` — loads HySpell's Reformed↔Classical mapping tables
- `conv.convert_word("reformed_form")` → Classical equivalent
- `conv.convert_text("reformed text")` → full text conversion (preserves whitespace/punctuation)
- `conv.is_reformed("form")` → True if word has a different Classical spelling
- `conv.detect_reformed_words("text")` → list of (reformed, classical) pairs found
- Uses lexicon map (161K entries) for base forms, suffix rules (159 rules) for inflected forms

### glossary.py
- `Glossary.from_file(path)` — loads SmallArmDic.txt (19K Armenian headwords)
- `glossary.lookup("word")` → list of GlossaryEntry with `.pos`, `.definition`, `.is_transitive`
- POS tags normalized from Armenian abbreviations (գ.→NOUN, նրգ.→VERB_TR, etc.)

### engine.py
- `MorphEngine.from_config("hyw_augment.toml")` — loads everything from config
- `engine.analyze("form")` → list of AnalysisResult (first backend that hits)
- `engine.analyze_all("form")` → dict of backend name → results (every backend)
- `engine.analyze_batch(forms)` → efficient bulk analysis with automatic fallback
- `engine.validate("form")` → bool (checks Nayiri, Apertium, and Hunspell)
- `engine.suggest("form")` → spelling suggestions via Hunspell
- `engine.convert_reformed("text")` → Reformed-to-Classical orthography conversion
- `engine.detect_reformed("text")` → find Reformed-orthography words
- `engine.lookup_definition("word")` → glossary entries with POS + definitions
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

[hyspell]
dir = "/path/to/HySpell_3.0.1/Dictionaries"
```

With a config file present, the CLI loads everything automatically — no flags needed. All sections are optional.

### CLI

Analyze a word (uses all configured backends):
`python -m hyw_augment.cli --analyze "WORD"`

Generate forms from a lemma:
`python -m hyw_augment.cli --generate "LEMMA"`

Validate a word (checks Nayiri, Apertium, and Hunspell):
`python -m hyw_augment.cli --validate "WORD"`

Get spelling suggestions:
`python -m hyw_augment.cli --suggest "MISSPELLED_WORD"`

Convert Reformed (Eastern) orthography to Classical (Western):
`python -m hyw_augment.cli --convert "REFORMED_TEXT"`

Look up a word's definition:
`python -m hyw_augment.cli --define "WORD"`

Coverage check:
`python -m hyw_augment.cli --coverage`

Coverage with mismatch export:
`python -m hyw_augment.cli --coverage --mismatches data/mismatches.tsv`

Override config with explicit flags:
`python -m hyw_augment.cli --nayiri data/*.json --apertium /path/to/apertium-hyw --analyze "WORD"`
`python -m hyw_augment.cli --hyspell /path/to/Dictionaries --validate "WORD"`

Extract mismatched words between UD and Nayiri (first pass for building function words list):
```
python -m hyw_augment.extract_words_from_UD \
    --conllu data/*.conllu \
    --nayiri data/nayiri-armenian-lexicon-2026-02-15-v1.json \
    --output data/extracted-words.json \
    --indent \
    --min-freq 3 # can adapt up or down
```

### External tool setup

#### Apertium transducer (morphological analysis/generation)

For expanded morphological coverage, install the Apertium Western Armenian transducer:

1. Install system packages: `hfst`, `lttoolbox`, `apertium`, `vislcg3`
2. Clone and build `lexd` (available in `apertium-tools`, but not standard `apertium`) : https://github.com/apertium/lexd
3. Clone and build: https://github.com/apertium/apertium-hyw
4. Set the `dir` in `hyw_augment.toml` under `[apertium]`

#### HySpell (spell checking, orthography conversion, glossary)

1. Install `hunspell` (usually available via system package manager; e.g. `pacman -S hunspell` on Arch, `apt install hunspell` on Debian/Ubuntu)
2. Clone: https://github.com/hyspell/HySpell_3.0.1
3. Set `dir` in `hyw_augment.toml` under `[hyspell]` to the `Dictionaries/` subdirectory

The spell checker requires the `hunspell` binary in PATH. The orthography converter and glossary are pure Python and work without it.

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

# Validate a word (checks all backends + spell checker)
engine.validate("WORD")  # True/False

# Spelling suggestions
engine.suggest("MISSPELLED_WORD")  # ["suggestion1", "suggestion2", ...]

# Convert Reformed (Eastern) orthography to Classical (Western)
engine.convert_reformed("reformed text")  # "classical text"

# Detect Reformed words in text
engine.detect_reformed("mixed text")  # [("reformed_word", "classical_word"), ...]

# Look up definitions
entries = engine.lookup_definition("WORD")
for e in entries:
    print(e.pos, e.definition)  # NOUN, Armenian definition text

# Treebank exploration
from hyw_augment import Treebank
tb = Treebank.from_dir("data/")
tb.vocab()                        # lemma -> set of observed surface forms
tb.pos_distribution()
tb.deprel_distribution()
```


## Current questions

- Right now, I am basically requiring classical orthography, but I, and many heritage speakers in the diaspora, write in a more mixed mode, especially if we've spent any time in Hayastan or interacting with Hayastansi output. The current approach is helpful for reinforcing the traditional mode, and I can normalize input, but is it wrong for Western Armenian spelling to drift closer to the reform style?

- What sort of word is է and similar? An auxilary? A function word? A suffix? It is obviously all of these, but how best to integrate? Need to make list of function words separate from words missing from Nayiri lexicon in general (lexicon is stated on project page to be incomplete/rolling release). currently in progress -- have extracted word list. also need to check to see if this is redundant given apertium/hyspell integration, or if would be better served by extracting these from there.

- Currently this is working on inflectional morphology, ie we're taking lemmas and giving them word forms. But Armenian is (at least somewhat) agglutinative. How to handle derivational morphology (ie building words from word-bits)? For example, in present setup from Nayiri, "անհատ" is one lexeme/lemma; but it's also ան = without հատ = one discrete unit, and native speakers would recognize this pattern. A parser should too, and this does not. Quick'n'dirty step one is to do stripping based on set prefix/suffix list: need to make. And then rules for how the words sometimes change when these attach. Future steps may lead towards a cleaner, more built out finite state transducer. Also need to check to see how Apertium handles this -- paper by Dolatian et al states that they built out rudimentary ruleset, and getting into the details might be worthwhile. HySpell also very clearly does something here.


## Grab-bag of small(er) TODOs/stretch goals/related project ideas:

  - clean up code
  - find/make/grab more texts, especially colloquial ones
  - create minimap of different latinizations
  - use actual branches instead of doing active development inside of main (sorry -- wanted to get this off the ground fast, and show work to anyone interested!)
