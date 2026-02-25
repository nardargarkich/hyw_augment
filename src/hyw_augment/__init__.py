"""hyw-augment: Western Armenian morphological augmentation layer for LLMs."""

from hyw_augment.conllu import Treebank, Sentence, Token
from hyw_augment.nayiri import Lexicon, MorphAnalysis
from hyw_augment.coverage import check_coverage
from hyw_augment.apertium import ApertiumAnalyzer, ApertiumAnalysis
from hyw_augment.engine import MorphEngine, AnalysisResult
from hyw_augment.spelling import SpellChecker
from hyw_augment.orthography import OrthographyConverter
from hyw_augment.glossary import Glossary, GlossaryEntry

__all__ = [
    "Treebank", "Sentence", "Token",
    "Lexicon", "MorphAnalysis",
    "ApertiumAnalyzer", "ApertiumAnalysis",
    "MorphEngine", "AnalysisResult",
    "SpellChecker", "OrthographyConverter",
    "Glossary", "GlossaryEntry",
    "check_coverage",
]
