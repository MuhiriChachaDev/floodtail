"""Model registry: versioned artifacts + SHA-256 integrity."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

import joblib

ModelType = Literal["hazard", "vulnerability"]


@dataclass
class RegistryEntry:
    model_type: ModelType
    version: str
    path: Path
    sha256: str
    metrics: dict[str, Any]
    params: dict[str, Any]
    feature_schema: dict[str, Any]
    training_card: dict[str, Any]
    pinned: bool = False


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class ModelRegistry:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def model_dir(self, model_type: ModelType, version: str) -> Path:
        return self.root / model_type / version

    def register(
        self,
        model_type: ModelType,
        artifact: Any,
        *,
        feature_builder_state: dict[str, Any],
        metrics: dict[str, Any],
        params: dict[str, Any],
        feature_schema: dict[str, Any],
        training_card: dict[str, Any],
        version: Optional[str] = None,
        pin: bool = True,
    ) -> RegistryEntry:
        version = version or _utc_stamp()
        dest = self.model_dir(model_type, version)
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)

        model_path = dest / "model.joblib"
        joblib.dump(
            {"model": artifact, "feature_builder": feature_builder_state},
            model_path,
        )
        _write_json(dest / "metrics.json", metrics)
        _write_json(dest / "params.json", params)
        _write_json(dest / "feature_schema.json", feature_schema)
        _write_json(dest / "TRAINING_CARD.json", training_card)

        sha = _sha256_file(model_path)
        (dest / "SHA256").write_text(sha + "\n", encoding="utf-8")

        if pin:
            self.pin_default(model_type, version)

        return RegistryEntry(
            model_type=model_type,
            version=version,
            path=dest,
            sha256=sha,
            metrics=metrics,
            params=params,
            feature_schema=feature_schema,
            training_card=training_card,
            pinned=pin,
        )

    def pin_default(self, model_type: ModelType, version: str) -> None:
        pin_path = self.root / model_type / "PINNED"
        pin_path.parent.mkdir(parents=True, exist_ok=True)
        pin_path.write_text(version.strip() + "\n", encoding="utf-8")

    def get_pinned(self, model_type: ModelType) -> Optional[str]:
        pin_path = self.root / model_type / "PINNED"
        if not pin_path.exists():
            return None
        return pin_path.read_text(encoding="utf-8").strip() or None

    def verify_integrity(self, model_type: ModelType, version: str) -> bool:
        dest = self.model_dir(model_type, version)
        model_path = dest / "model.joblib"
        sha_path = dest / "SHA256"
        if not model_path.exists() or not sha_path.exists():
            return False
        expected = sha_path.read_text(encoding="utf-8").strip()
        return _sha256_file(model_path) == expected

    def load(self, model_type: ModelType, version: Optional[str] = None) -> tuple[Any, dict[str, Any], RegistryEntry]:
        version = version or self.get_pinned(model_type)
        if not version:
            raise FileNotFoundError(f"No pinned {model_type} model in {self.root}")
        dest = self.model_dir(model_type, version)
        if not dest.exists():
            raise FileNotFoundError(f"Missing model artifact: {dest}")
        if not self.verify_integrity(model_type, version):
            raise ValueError(f"SHA-256 mismatch for {model_type}/{version}")
        blob = joblib.load(dest / "model.joblib")
        entry = RegistryEntry(
            model_type=model_type,
            version=version,
            path=dest,
            sha256=(dest / "SHA256").read_text(encoding="utf-8").strip(),
            metrics=_read_json(dest / "metrics.json") if (dest / "metrics.json").exists() else {},
            params=_read_json(dest / "params.json") if (dest / "params.json").exists() else {},
            feature_schema=_read_json(dest / "feature_schema.json")
            if (dest / "feature_schema.json").exists()
            else {},
            training_card=_read_json(dest / "TRAINING_CARD.json")
            if (dest / "TRAINING_CARD.json").exists()
            else {},
            pinned=self.get_pinned(model_type) == version,
        )
        return blob["model"], blob["feature_builder"], entry

    def list_models(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for model_type in ("hazard", "vulnerability"):
            base = self.root / model_type
            if not base.exists():
                continue
            pinned = self.get_pinned(model_type)  # type: ignore[arg-type]
            for child in sorted(p for p in base.iterdir() if p.is_dir()):
                sha_path = child / "SHA256"
                out.append(
                    {
                        "model_type": model_type,
                        "version": child.name,
                        "pinned": pinned == child.name,
                        "path": str(child),
                        "sha256": sha_path.read_text(encoding="utf-8").strip()
                        if sha_path.exists()
                        else None,
                        "integrity_ok": self.verify_integrity(model_type, child.name),  # type: ignore[arg-type]
                    }
                )
        return out
