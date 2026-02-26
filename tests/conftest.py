"""Shared test fixtures."""

import tomllib
from pathlib import Path

import pytest


def _find_config() -> Path | None:
    """Find hyw_augment.toml from the project root."""
    for base in [Path("."), Path("..")]:
        p = base / "hyw_augment.toml"
        if p.exists():
            return p.resolve()
    return None


def find_data(filename: str) -> Path | None:
    """Find a data file relative to the project root."""
    for base in [Path("data"), Path("../data")]:
        p = base / filename
        if p.exists():
            return p
    return None


@pytest.fixture
def hyspell_dir() -> Path:
    """Resolve the HySpell Dictionaries path from hyw_augment.toml.

    Skips the test if the config or directory is not found.
    """
    config_path = _find_config()
    if config_path is None:
        pytest.skip("hyw_augment.toml not found")

    with config_path.open("rb") as f:
        cfg = tomllib.load(f)

    hs_dir = cfg.get("hyspell", {}).get("dir")
    if not hs_dir:
        pytest.skip("[hyspell] dir not configured in hyw_augment.toml")

    hp = Path(hs_dir)
    if not hp.is_absolute():
        hp = config_path.parent / hp

    if not hp.exists():
        pytest.skip(f"HySpell directory not found: {hp}")

    return hp
