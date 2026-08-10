"""JSON file helpers for pipeline data stores."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
MOCKS_DIR = PROJECT_ROOT / "mocks"
SEED_DIR = PROJECT_ROOT / "seed"


def load_json(path: Path | str) -> object:
    """Load and parse a JSON file, raising a clear error if missing or malformed."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    try:
        with file_path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in {file_path}: {exc}") from exc


def save_json(path: Path, payload: object) -> None:
    """Write a JSON-serializable payload to disk with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def load_mock(name: str) -> object:
    """Load a fixture from the mocks directory by filename."""
    return load_json(MOCKS_DIR / name)


def load_store(filename: str) -> list[dict[str, object]]:
    """Load a list-backed data store from data/."""
    payload = load_json(DATA_DIR / filename)
    if not isinstance(payload, list):
        raise ValueError(f"Expected list in data/{filename}, got {type(payload).__name__}")
    return payload


def save_store(filename: str, records: list[dict[str, object]]) -> None:
    """Persist records to a list-backed data store under data/."""
    save_json(DATA_DIR / filename, records)


def upsert_record(
    filename: str,
    record: dict[str, object],
    key_field: str,
) -> None:
    """Insert or replace a record in a JSON store keyed by key_field."""
    records = load_store(filename)
    record_id = record[key_field]
    updated = [item for item in records if item.get(key_field) != record_id]
    updated.append(record)
    save_store(filename, updated)
