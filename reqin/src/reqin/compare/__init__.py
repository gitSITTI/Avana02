"""The comparison engine, stages 1 to 4 of the research report: no AI, no network, deterministic. See docs/COMPARE_FORMAT.md.

    from reqin.compare import compare_dataset
    result, manifest_sha = compare_dataset("path/to/dataset")      # refuses a dataset that fails its contract
"""
from __future__ import annotations

from .engine import ENGINE, Result, Settings, compare
from .output import FORMAT, CompareError, check, run_dataset, write
from .rules import RULES, TYPES, classify
from .slots import Slots, extract
from . import vocabulary
from .vocabulary import Vocabulary, load as load_vocabulary

compare_dataset = run_dataset

__all__ = ["ENGINE", "FORMAT", "RULES", "TYPES", "CompareError", "Result", "Settings", "Slots", "Vocabulary", "check", "classify", "compare", "compare_dataset", "extract", "load_vocabulary", "run_dataset", "vocabulary", "write"]
