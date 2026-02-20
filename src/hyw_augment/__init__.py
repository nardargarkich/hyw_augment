"""hyw-augment: Western Armenian morphological augmentation layer for LLMs."""

from hyw_augment.conllu import Treebank, Sentence, Token
from hyw_augment.nayiri import Lexicon, MorphAnalysis
from hyw_augment.coverage import check_coverage

__all__ = [
    "Treebank", "Sentence", "Token",
    "Lexicon", "MorphAnalysis",
    "check_coverage",
]
