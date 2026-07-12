from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def duplicate_key(product_name: str, destination_url: str, board_id: str, headline: str) -> str:
    raw = "|".join([product_name.strip().lower(), destination_url, board_id, headline.lower()])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def already_exists(history_path: Path, key: str) -> bool:
    if not history_path.exists():
        return False
    for line in history_path.read_text(encoding="utf-8").splitlines():
        try:
            if json.loads(line).get("duplicate_key") == key:
                return True
        except json.JSONDecodeError:
            continue
    return False


def append_history(history_path: Path, record: dict) -> None:
    record = dict(record)
    record["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    with history_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
