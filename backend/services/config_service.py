import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from models.forecast import ConfigRecord, ConfigScope, ConfigUpdate

logger = logging.getLogger(__name__)


class ConfigService:
    """File-based configuration versioning service."""

    def __init__(self, config_dir: str = "storage/configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.history_path = self.config_dir / "config_history.jsonl"
        self.latest_path = self.config_dir / "latest.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_latest_config(self) -> Dict[str, Any]:
        if self.latest_path.exists():
            with self.latest_path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        default = {
            "version": "0.0.0",
            "updated_at": None,
            "global": {},
            "per_sku": {},
        }
        return default

    def append_update(self, update: ConfigUpdate) -> ConfigRecord:
        latest = self.get_latest_config()
        per_sku = latest.setdefault("per_sku", {})
        global_cfg = latest.setdefault("global", {})

        if update.scope == ConfigScope.GLOBAL:
            global_cfg.update(update.settings)
        else:
            target = update.target or "default"
            sku_cfg = per_sku.get(target, {})
            sku_cfg.update(update.settings)
            per_sku[target] = sku_cfg

        timestamp = datetime.utcnow().isoformat()
        version = self._bump_patch_version(latest.get("version", "0.0.0"))

        record = ConfigRecord(
            timestamp=timestamp,
            version=version,
            scope=update.scope,
            target=update.target,
            settings=update.settings,
            author=update.author,
        )

        self._append_history(record)

        latest["version"] = version
        latest["updated_at"] = timestamp
        latest["global"] = global_cfg
        latest["per_sku"] = per_sku
        self._write_latest(latest)

        return record

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        if not self.history_path.exists():
            return []

        records: List[Dict[str, Any]] = []
        with self.history_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:  # pragma: no cover
                    logger.warning("Skipping invalid config record: %s", exc)
        if limit is not None:
            return records[-limit:]
        return records

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _write_latest(self, payload: Dict[str, Any]) -> None:
        with self.latest_path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

    def _append_history(self, record: ConfigRecord) -> None:
        with self.history_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.dict(), ensure_ascii=False) + "\n")

    def _bump_patch_version(self, version: str) -> str:
        try:
            major, minor, patch = [int(part) for part in version.split(".")]
        except ValueError:
            major, minor, patch = 0, 0, 0
        patch += 1
        return f"{major}.{minor}.{patch}"
