"""FLOODTAIL — Decision Support, Governance & Human-in-the-Loop Engine.

Assembles comprehensive decision evidence packages, evaluates multi-factor
confidence models (4-quadrant Risk vs Confidence), generates underwriting
recommendations, and enforces human decision capture with mandatory audit tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from src.audit_log import AuditManager, AuditRecord
from src.exceptions import ValidationError
from src.logging_config import get_logger

logger = get_logger("decision")


@dataclass
class DecisionConfidence:
    """Quantitative decision confidence model and 4-quadrant categorization."""

    level: Literal["HIGH", "MEDIUM", "LOW"]
    score: float
    quadrant: Literal[
        "HIGH_RISK_HIGH_CONFIDENCE",
        "HIGH_RISK_LOW_CONFIDENCE",
        "LOW_RISK_HIGH_CONFIDENCE",
        "LOW_RISK_LOW_CONFIDENCE",
    ]
    factors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class DecisionEvidencePackage:
    """Comprehensive, structured underwriting decision evidence container."""

    run_id: str
    policy_id: str
    recommendation: Literal["ACCEPT", "REVIEW", "ESCALATE"]
    confidence: DecisionConfidence
    key_metrics: dict[str, float]
    data_quality_summary: dict[str, Any]
    hazard_summary: dict[str, Any]
    vulnerability_summary: dict[str, Any]
    loss_summary: dict[str, Any]
    accumulation_summary: dict[str, Any]
    tail_summary: dict[str, Any]
    pricing_summary: dict[str, Any]
    risk_appetite_summary: dict[str, Any]
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    evidence_refs: dict[str, Any] = field(default_factory=dict)
    model_version: str = "v1.0"
    data_version: str = "v1.0"


@dataclass
class UnderwritingDecision:
    """Final business decision object linking AI recommendation with human action."""

    policy_id: str
    recommendation: Literal["ACCEPT", "REVIEW", "ESCALATE"]
    human_decision: Optional[Literal["ACCEPT", "MODIFY", "REJECT"]]
    reason: Optional[str]
    original_premium: float
    final_premium: float
    user: Optional[str]
    timestamp: str
    run_id: str
    model_version: str
    data_version: str
    confidence: str
    status: Literal["AWAITING_HUMAN", "RECORDED", "BLOCKED"]
    audit_record_id: Optional[int] = None


class DecisionEngine:
    """Evaluates decision support evidence and records human underwriting actions."""

    def __init__(self, audit_manager: Optional[AuditManager] = None) -> None:
        self.audit_manager = audit_manager

    @staticmethod
    def evaluate_confidence(
        data_quality_score: float,
        critical_issues_count: int,
        simulation_years: int,
        is_benchmark_vulnerability: bool = True,
        tail_year_count: int = 4,
        is_high_risk: bool = False,
    ) -> DecisionConfidence:
        """Compute a transparent, deterministic decision confidence score."""
        score = 1.0
        factors = []
        warnings = []

        # Data quality factor
        if data_quality_score >= 90.0:
            factors.append(f"Data quality is high ({data_quality_score:.1f}% score).")
        elif data_quality_score >= 70.0:
            score -= 0.20
            factors.append(f"Data quality is moderate ({data_quality_score:.1f}% score).")
        else:
            score -= 0.45
            factors.append(f"Data quality is low ({data_quality_score:.1f}% score).")
            warnings.append("LOW_DATA_QUALITY")

        if critical_issues_count > 0:
            score -= min(0.35, critical_issues_count * 0.15)
            warnings.append(f"CRITICAL_DATA_ISSUES ({critical_issues_count})")

        # Simulation sample support
        if simulation_years < 10000:
            score -= 0.15
            warnings.append("LIMITED_SIMULATION_SUPPORT")
            factors.append(
                f"Simulation depth ({simulation_years:,} years) yields {tail_year_count} tail observations; "
                "larger depth recommended for production."
            )
        else:
            factors.append(f"Robust simulation depth ({simulation_years:,} years, {tail_year_count} tail events).")

        # Vulnerability calibration factor
        if is_benchmark_vulnerability:
            score -= 0.10
            warnings.append("BENCHMARK_VULNERABILITY_CURVE")
            factors.append("Using prototype benchmark vulnerability curve; Kenya-specific calibration not established.")

        score = max(0.0, min(1.0, score))

        if score >= 0.75:
            level = "HIGH"
        elif score >= 0.50:
            level = "MEDIUM"
        else:
            level = "LOW"

        # 4-Quadrant mapping
        if is_high_risk:
            quadrant = "HIGH_RISK_HIGH_CONFIDENCE" if level == "HIGH" else "HIGH_RISK_LOW_CONFIDENCE"
        else:
            quadrant = "LOW_RISK_HIGH_CONFIDENCE" if level == "HIGH" else "LOW_RISK_LOW_CONFIDENCE"

        return DecisionConfidence(
            level=level,
            score=round(score, 3),
            quadrant=quadrant,
            factors=factors,
            warnings=warnings,
        )

    def assemble_evidence_package(
        self,
        run_id: str,
        policy_id: str,
        recommendation: Literal["ACCEPT", "REVIEW", "ESCALATE"],
        key_metrics: dict[str, float],
        data_quality_summary: dict[str, Any],
        hazard_summary: dict[str, Any],
        vulnerability_summary: dict[str, Any],
        loss_summary: dict[str, Any],
        accumulation_summary: dict[str, Any],
        tail_summary: dict[str, Any],
        pricing_summary: dict[str, Any],
        risk_appetite_summary: dict[str, Any],
        reasons: list[str],
        warnings: list[str],
        assumptions: list[str],
        evidence_refs: dict[str, Any],
        simulation_years: int = 1000,
        model_version: str = "v1.0",
        data_version: str = "v1.0",
    ) -> DecisionEvidencePackage:
        """Create a complete, typed DecisionEvidencePackage."""
        is_high_risk = recommendation in ("REVIEW", "ESCALATE")
        dq_score = float(data_quality_summary.get("quality_score", 100.0))
        crit_issues = int(data_quality_summary.get("critical_issues_count", 0))
        tail_years = int(tail_summary.get("tail_year_count", 4))

        confidence = self.evaluate_confidence(
            data_quality_score=dq_score,
            critical_issues_count=crit_issues,
            simulation_years=simulation_years,
            is_benchmark_vulnerability=True,
            tail_year_count=tail_years,
            is_high_risk=is_high_risk,
        )

        all_warnings = sorted(list(set(warnings + confidence.warnings)))

        return DecisionEvidencePackage(
            run_id=run_id,
            policy_id=policy_id,
            recommendation=recommendation,
            confidence=confidence,
            key_metrics=key_metrics,
            data_quality_summary=data_quality_summary,
            hazard_summary=hazard_summary,
            vulnerability_summary=vulnerability_summary,
            loss_summary=loss_summary,
            accumulation_summary=accumulation_summary,
            tail_summary=tail_summary,
            pricing_summary=pricing_summary,
            risk_appetite_summary=risk_appetite_summary,
            reasons=reasons,
            warnings=all_warnings,
            assumptions=assumptions,
            evidence_refs=evidence_refs,
            model_version=model_version,
            data_version=data_version,
        )

    def record_human_decision(
        self,
        evidence: DecisionEvidencePackage,
        human_decision: Literal["ACCEPT", "MODIFY", "REJECT"],
        user: str,
        reason: Optional[str] = None,
        modified_premium: Optional[float] = None,
    ) -> UnderwritingDecision:
        """Process and record a human underwriting decision, appending to audit log."""
        user_clean = user.strip()
        if not user_clean:
            raise ValidationError("Underwriting decision requires a valid user identity.")

        h_decision = human_decision.strip().upper()
        if h_decision not in ("ACCEPT", "MODIFY", "REJECT"):
            raise ValidationError(f"Invalid decision '{human_decision}'. Must be ACCEPT, MODIFY, or REJECT.")

        orig_premium = float(evidence.key_metrics.get("technical_premium", 0.0))

        if h_decision == "MODIFY":
            if modified_premium is None or modified_premium <= 0:
                raise ValidationError("Modified decision requires a positive modified_premium value.")
            if not reason or not reason.strip():
                raise ValidationError("A clear justification reason is mandatory when modifying technical premium.")
            final_premium = float(modified_premium)
        elif h_decision == "REJECT":
            if not reason or not reason.strip():
                raise ValidationError("A clear justification reason is mandatory when rejecting a policy.")
            final_premium = 0.0
        else:  # ACCEPT
            final_premium = orig_premium

        audit_record_id = None
        if self.audit_manager:
            rec = self.audit_manager.append_decision(
                run_id=evidence.run_id,
                policy_id=evidence.policy_id,
                user=user_clean,
                recommendation=evidence.recommendation,
                final_decision=h_decision,
                original_premium=orig_premium,
                new_premium=final_premium,
                reason=reason,
                model_version=evidence.model_version,
                data_version=evidence.data_version,
            )
            audit_record_id = rec.id

        ts = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Human decision recorded: [policy=%s, ai_rec=%s, human=%s, orig_prem=$%.2f, final_prem=$%.2f, user=%s]",
            evidence.policy_id,
            evidence.recommendation,
            h_decision,
            orig_premium,
            final_premium,
            user_clean,
        )

        return UnderwritingDecision(
            policy_id=evidence.policy_id,
            recommendation=evidence.recommendation,
            human_decision=h_decision,  # type: ignore[arg-type]
            reason=reason.strip() if reason else None,
            original_premium=round(orig_premium, 2),
            final_premium=round(final_premium, 2),
            user=user_clean,
            timestamp=ts,
            run_id=evidence.run_id,
            model_version=evidence.model_version,
            data_version=evidence.data_version,
            confidence=evidence.confidence.level,
            status="RECORDED",
            audit_record_id=audit_record_id,
        )
