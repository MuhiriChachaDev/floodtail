"""FLOODTAIL — Cryptographic Audit Log & Decision Governance Engine.

Provides an immutable, append-only hash-chained audit trail for all
underwriting decisions, policy actions, and manual overrides.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.database import DatabaseManager, get_connection
from src.exceptions import DatabaseError, ValidationError
from src.logging_config import get_logger

logger = get_logger("audit_log")

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditRecord:
    """Immutable audit record representing a recorded underwriting decision."""

    id: Optional[int]
    timestamp: str
    run_id: str
    policy_id: str
    user: str
    recommendation: str
    final_decision: str
    original_premium: float
    new_premium: float
    reason: Optional[str]
    model_version: str
    data_version: str
    decision_hash: str
    previous_hash: str


@dataclass
class AuditVerificationResult:
    """Result of verifying the cryptographic audit log hash chain."""

    is_valid: bool
    record_count: int
    broken_index: Optional[int] = None
    expected_hash: Optional[str] = None
    actual_hash: Optional[str] = None
    message: str = "Audit chain is valid and untampered."


def calculate_decision_hash(
    previous_hash: str,
    timestamp: str,
    run_id: str,
    policy_id: str,
    user: str,
    recommendation: str,
    final_decision: str,
    original_premium: float,
    new_premium: float,
    reason: Optional[str],
    model_version: str,
    data_version: str,
) -> str:
    """Compute SHA-256 hash for an audit record linked to its predecessor."""
    reason_str = (reason or "").strip()
    payload = (
        f"{previous_hash}|{timestamp}|{run_id}|{policy_id}|{user}|"
        f"{recommendation}|{final_decision}|{original_premium:.2f}|{new_premium:.2f}|"
        f"{reason_str}|{model_version}|{data_version}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditManager:
    """Manages the append-only cryptographic audit trail in SQLite."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager()

    def get_latest_hash(self) -> str:
        """Retrieve the hash of the most recently inserted audit record."""
        sql = "SELECT decision_hash FROM audit_log ORDER BY id DESC LIMIT 1"
        try:
            with get_connection(self.db.db_path) as conn:
                row = conn.execute(sql).fetchone()
                if row and row["decision_hash"]:
                    return str(row["decision_hash"])
                return GENESIS_HASH
        except Exception as exc:
            logger.error("Failed to fetch latest audit hash: %s", exc)
            raise DatabaseError(f"Audit log query failed: {exc}") from exc

    def append_decision(
        self,
        run_id: str,
        policy_id: str,
        user: str,
        recommendation: str,
        final_decision: str,
        original_premium: float,
        new_premium: float,
        model_version: str,
        data_version: str = "v1.0",
        reason: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> AuditRecord:
        """Append a new underwriting decision to the cryptographic audit chain.

        Enforces non-empty reason when decision deviates from AI recommendation.
        """
        user_clean = user.strip()
        if not user_clean:
            raise ValidationError("Audit record requires a valid user identity.")

        if not policy_id.strip():
            raise ValidationError("Audit record requires a valid policy_id.")

        final_clean = final_decision.strip().upper()
        if final_clean not in ("ACCEPT", "MODIFY", "REJECT"):
            raise ValidationError(f"Invalid human decision '{final_decision}'. Must be ACCEPT, MODIFY, or REJECT.")

        # Require reason when modifying or rejecting
        if final_clean in ("MODIFY", "REJECT") and (not reason or not reason.strip()):
            raise ValidationError(f"A non-empty justification reason is mandatory when {final_clean}ing a policy.")

        ts = timestamp or datetime.now(timezone.utc).isoformat()
        previous_hash = self.get_latest_hash()

        decision_hash = calculate_decision_hash(
            previous_hash=previous_hash,
            timestamp=ts,
            run_id=run_id,
            policy_id=policy_id,
            user=user_clean,
            recommendation=recommendation,
            final_decision=final_clean,
            original_premium=original_premium,
            new_premium=new_premium,
            reason=reason,
            model_version=model_version,
            data_version=data_version,
        )

        sql = """
        INSERT INTO audit_log (
            timestamp, run_id, policy_id, user, recommendation,
            final_decision, original_premium, new_premium, reason,
            model_version, data_version, decision_hash, previous_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with get_connection(self.db.db_path) as conn:
                cursor = conn.execute(
                    sql,
                    (
                        ts,
                        run_id,
                        policy_id,
                        user_clean,
                        recommendation,
                        final_clean,
                        original_premium,
                        new_premium,
                        reason.strip() if reason else None,
                        model_version,
                        data_version,
                        decision_hash,
                        previous_hash,
                    ),
                )
                record_id = cursor.lastrowid
        except Exception as exc:
            logger.error("Failed to append audit record: %s", exc)
            raise DatabaseError(f"Failed to record audit entry: {exc}") from exc

        logger.info(
            "Audit record appended [id=%d, policy=%s, decision=%s, hash=%s...]",
            record_id or 0,
            policy_id,
            final_clean,
            decision_hash[:12],
        )

        return AuditRecord(
            id=record_id,
            timestamp=ts,
            run_id=run_id,
            policy_id=policy_id,
            user=user_clean,
            recommendation=recommendation,
            final_decision=final_clean,
            original_premium=original_premium,
            new_premium=new_premium,
            reason=reason.strip() if reason else None,
            model_version=model_version,
            data_version=data_version,
            decision_hash=decision_hash,
            previous_hash=previous_hash,
        )

    def get_audit_records(
        self,
        policy_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> list[AuditRecord]:
        """Fetch audit records optionally filtered by policy_id or run_id."""
        clauses = []
        params = []
        if policy_id:
            clauses.append("policy_id = ?")
            params.append(policy_id)
        if run_id:
            clauses.append("run_id = ?")
            params.append(run_id)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM audit_log {where} ORDER BY id ASC"

        try:
            with get_connection(self.db.db_path) as conn:
                rows = conn.execute(sql, params).fetchall()
                return [
                    AuditRecord(
                        id=row["id"],
                        timestamp=row["timestamp"],
                        run_id=row["run_id"],
                        policy_id=row["policy_id"],
                        user=row["user"],
                        recommendation=row["recommendation"],
                        final_decision=row["final_decision"],
                        original_premium=float(row["original_premium"]),
                        new_premium=float(row["new_premium"]),
                        reason=row["reason"],
                        model_version=row["model_version"],
                        data_version=row["data_version"],
                        decision_hash=row["decision_hash"],
                        previous_hash=row["previous_hash"],
                    )
                    for row in rows
                ]
        except Exception as exc:
            logger.error("Failed to fetch audit records: %s", exc)
            raise DatabaseError(f"Audit log query failed: {exc}") from exc

    def verify_audit_chain(self) -> AuditVerificationResult:
        """Cryptographically verify that the entire audit chain is untampered."""
        records = self.get_audit_records()
        if not records:
            return AuditVerificationResult(is_valid=True, record_count=0, message="Audit log is empty.")

        expected_prev_hash = GENESIS_HASH
        for idx, rec in enumerate(records):
            # Check 1: Previous hash must match predecessor
            if rec.previous_hash != expected_prev_hash:
                logger.warning(
                    "Audit chain broken at record id=%s: expected prev_hash %s, found %s",
                    rec.id,
                    expected_prev_hash,
                    rec.previous_hash,
                )
                return AuditVerificationResult(
                    is_valid=False,
                    record_count=len(records),
                    broken_index=idx,
                    expected_hash=expected_prev_hash,
                    actual_hash=rec.previous_hash,
                    message=f"Hash chain broken at record {rec.id}: predecessor hash mismatch.",
                )

            # Check 2: Recalculate content hash
            recalc_hash = calculate_decision_hash(
                previous_hash=rec.previous_hash,
                timestamp=rec.timestamp,
                run_id=rec.run_id,
                policy_id=rec.policy_id,
                user=rec.user,
                recommendation=rec.recommendation,
                final_decision=rec.final_decision,
                original_premium=rec.original_premium,
                new_premium=rec.new_premium,
                reason=rec.reason,
                model_version=rec.model_version,
                data_version=rec.data_version,
            )

            if recalc_hash != rec.decision_hash:
                logger.warning(
                    "Audit content tampered at record id=%s: expected %s, found %s",
                    rec.id,
                    recalc_hash,
                    rec.decision_hash,
                )
                return AuditVerificationResult(
                    is_valid=False,
                    record_count=len(records),
                    broken_index=idx,
                    expected_hash=recalc_hash,
                    actual_hash=rec.decision_hash,
                    message=f"Record {rec.id} contents have been modified after insertion.",
                )

            expected_prev_hash = rec.decision_hash

        return AuditVerificationResult(
            is_valid=True,
            record_count=len(records),
            message=f"Audit chain verified successfully ({len(records)} records).",
        )
