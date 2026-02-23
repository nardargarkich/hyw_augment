# hyw_augment

## Project to augment LLMs for better Western Armenian language parsing

## WARNING! Still very much in development, many known issues

## What this is

A morphological augmentation layer for Western Armenian (hyw) LLMs. The goal is
to improve LLM output quality in Western Armenian by giving the model access to
structured linguistic data at inference time, rather than fine-tuning. (Fine tuning may come later. Currently early stage.)

This is **model-agnostic** — it sits between the user and any LLM (currently
targeting Ministral 14B via Ollama, but portable to anything).

## Why

- No conversational Western Armenian LLM exists yet
- Eastern Armenian has [HyGPT](https://huggingface.co/Gen2B/HyGPT-10b) and [ArmenianGPT](https://huggingface.co/ArmGPT/ArmenianGPT-0.1-12B); Western has nothing; even given that it should be easier to get an Eastern Armenian-speaking LLM to figure out Western Armenian, it would be nice to get up and running with higher-parameter models
- The NLP infrastructure is arriving (UD treebank, Nayiri lexicon, DALiH project)
  but nobody has connected it to conversational generation
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

## Architecture

```
src/hyw_augment/
├── __init__.py               # Package exports
├── __main__.py               # python -m hyw_augment
├── cli.py                    # CLI runner
├── extract_words_from_UD.py  # extracts unmatched words list from UD database in Nayiri format, with the goal of grabbing function words
├── conllu.py                 # CoNLL-U treebank parser
├── nayiri.py                 # Nayiri lexicon parser + morphological lookup
└── coverage.py               # Cross-reference treebank ↔ lexicon
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

## Usage

### CLI

Analyze a word — give it a surface form, get back all possible lemmas and grammatical analyses as currently documented
`bashpython -m hyw_augment.cli --nayiri data/*.json --analyze "արշաւը"`

Generate forms from a lemma — go the other direction, give it a dictionary form and see all its inflections
`bashpython -m hyw_augment.cli --nayiri data/*.json --generate "արշաւ"`

Checking coverage between current datasets
`python -m hyw_augment.cli --conllu data/*.conllu --nayiri data/nayiri-armenian-lexicon-2026-02-15-v1.json data/function-words.json --coverage`

Finding Nayiri/UD dataset mismatches
`python -m hyw_augment --conllu data/*.conllu --nayiri data/nayiri*.json --coverage --mismatches data/mismatches.tsv`

Finding dataset mismatches w/added wordlists
`python -m hyw_augment --conllu data/*.conllu --nayiri data/*.json --coverage --mismatches data/mismatches-ext.tsv`

extract mismatched words between UD and Nayiri
(first pass for building function words list)
```
python -m hyw_augment.extract_words_from_UD \
    --conllu data/*.conllu \
    --nayiri data/nayiri-armenian-lexicon-2026-02-15-v1.json \
    --output data/extracted-words.json \
    --indent \
    --min-freq 3 # can adapt up or down
```

### Python

Treebank exploration in Python
```
from hyw_augment import Treebank

tb = Treebank.from_dir("data/")
tb.vocab()           # lemma → set of observed surface forms
tb.pos_distribution()
tb.deprel_distribution()  # what dependency relations appear and how often

for sent in tb:
    root = sent.root()           # the main verb/predicate
    nouns = sent.by_upos("NOUN", "PROPN")  # filter by POS
    # each token has .form, .lemma, .upos, .feats, .deprel, .head
```


## Current questions

- What sort of word is է and similar? An auxilary? A function word? A suffix? It is obviously all of these, but how best to integrate? Need to make list of function words separate from words missing from Nayiri lexicon in general (lexicon is stated on project page to be incomplete/rolling release).
- Somewhat similarly: currently this is working on inflectional morphology, ie we're taking lemmas and giving them word forms. But Armenian is (at least somewhat) agglutinative. How to handle derivational morphology (ie building words from word-bits)? In present setup from Nayiri, "անհատ" is one lexeme/lemma; but it's also ան = without հատ = one discrete unit, and native speakers would recognize this pattern. A parser should too. Quick'n'dirty step one is to do stripping based on set prefix/suffix list: need to make. Future steps lead towards a finite state transducer type thing, which will take... a while.


## Grab-bag of small(er) TODOs/stretch goals/related project ideas:

  - clean up code
  - find/make/grab more texts, especially colloquial ones
  - create minimap of different latinizations

