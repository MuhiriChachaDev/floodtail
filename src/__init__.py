"""FLOODTAIL — Flood catastrophe and reinsurance decision-intelligence system."""

from src.accumulation import (
    AccumulationAnalysisResult,
    CoHitPolicyMetric,
    PortfolioAccumulationEngine,
    PropertyTypeAccumulation,
    RegionalAccumulation,
)
from src.catastrophe_store import (
    CatastrophePipeline,
    CatastropheRunResult,
    run_catastrophe_model,
)
from src.config import FLOODTAILConfig, load_config
from src.counterfactual import (
    CounterfactualEngine,
    MarginalRiskImpact,
    RiskAppetiteConfig,
    RiskAppetiteRuleEngine,
    RiskRecommendation,
    WhatIfSensitivityResult,
)
from src.database import DatabaseManager, initialize_database
from src.events import EventCatalogue, EventOccurrence, EventSimulator
from src.exceptions import (
    ConfigurationError,
    DatabaseError,
    DataQualityError,
    EventSetError,
    FloodtailError,
    GovernanceError,
    HazardInputError,
    HazardModelError,
    IngestionError,
    LossCalculationError,
    ModelCalculationError,
    ReconciliationError,
    SchemaValidationError,
    VulnerabilityError,
    VulnerabilityModelError,
)
from src.hazard import FootprintGeometry, HazardFootprintStore, SpatialHazardEngine
from src.ingestion import IngestionEngine, IngestionResult
from src.logging_config import get_logger, setup_logging
from src.loss import CatastropheLossEngine, ReconciliationReport
from src.normalizer import NormalizationResult, PortfolioNormalizer
from src.portfolio_store import PortfolioStore, VersionMetadata
from src.pricing import PolicyPriceBreakdown, PortfolioPricingResult, TechnicalPricingEngine
from src.quality import DataQualityAuditor, QualityProfile, QualityReport
from src.risk_metrics import ExceedancePoint, RiskMetricsEngine, RiskMetricsSummary, TailSetDetails
from src.risk_store import RiskAnalyticsPipeline, RiskAnalyticsResult, run_risk_analytics
from src.schema_mapper import ColumnMapping, MappingPlan, SchemaMapper
from src.schemas import (
    AgentResult,
    AgentStatus,
    AnnualLossResult,
    EventRecord,
    HazardResult,
    LossResult,
    PolicyTailResult,
    PortfolioRecord,
    PricingResult,
    RunContext,
    VulnerabilityResult,
)
from src.tail_risk import (
    PolicyTailContributionRecord,
    PolicyTailRiskEngine,
    TailRiskAllocationResult,
)
from src.vulnerability import VulnerabilityCurve, VulnerabilityEngine

from src.agent_orchestrator import (
    AgentOrchestrator,
    AgentTraceStep,
    AgentWorkflowTrace,
    WorkflowExecutionResult,
)
from src.audit_log import (
    AuditManager,
    AuditRecord,
    AuditVerificationResult,
    calculate_decision_hash,
)
from src.decision import (
    DecisionConfidence,
    DecisionEngine,
    DecisionEvidencePackage,
    UnderwritingDecision,
)
from src.explainability import (
    AccumulationExplanation,
    ExplainabilityEngine,
    MathematicalTrace,
    MathematicalTraceStep,
    PolicyExplanation,
    PriceExplanation,
    RecommendationExplanation,
    TVaRExplanation,
)

__all__ = [
    "AccumulationAnalysisResult",
    "AccumulationExplanation",
    "AgentOrchestrator",
    "AgentResult",
    "AgentStatus",
    "AgentTraceStep",
    "AgentWorkflowTrace",
    "AnnualLossResult",
    "AuditManager",
    "AuditRecord",
    "AuditVerificationResult",
    "CatastropheLossEngine",
    "CatastrophePipeline",
    "CatastropheRunResult",
    "CoHitPolicyMetric",
    "ColumnMapping",
    "ConfigurationError",
    "CounterfactualEngine",
    "DataQualityAuditor",
    "DataQualityError",
    "DatabaseError",
    "DatabaseManager",
    "DecisionConfidence",
    "DecisionEngine",
    "DecisionEvidencePackage",
    "EventCatalogue",
    "EventOccurrence",
    "EventRecord",
    "EventSetError",
    "EventSimulator",
    "ExceedancePoint",
    "ExplainabilityEngine",
    "FLOODTAILConfig",
    "FloodtailError",
    "FootprintGeometry",
    "GovernanceError",
    "HazardFootprintStore",
    "HazardInputError",
    "HazardModelError",
    "HazardResult",
    "IngestionEngine",
    "IngestionError",
    "IngestionResult",
    "LossCalculationError",
    "LossResult",
    "MappingPlan",
    "MarginalRiskImpact",
    "MathematicalTrace",
    "MathematicalTraceStep",
    "ModelCalculationError",
    "NormalizationResult",
    "PolicyExplanation",
    "PolicyPriceBreakdown",
    "PolicyTailContributionRecord",
    "PolicyTailResult",
    "PolicyTailRiskEngine",
    "PortfolioAccumulationEngine",
    "PortfolioNormalizer",
    "PortfolioPricingResult",
    "PortfolioRecord",
    "PortfolioStore",
    "PriceExplanation",
    "PricingResult",
    "PropertyTypeAccumulation",
    "QualityProfile",
    "QualityReport",
    "RecommendationExplanation",
    "ReconciliationError",
    "ReconciliationReport",
    "RegionalAccumulation",
    "RiskAnalyticsPipeline",
    "RiskAnalyticsResult",
    "RiskAppetiteConfig",
    "RiskAppetiteRuleEngine",
    "RiskMetricsEngine",
    "RiskMetricsSummary",
    "RiskRecommendation",
    "RunContext",
    "SchemaMapper",
    "SchemaValidationError",
    "SpatialHazardEngine",
    "TVaRExplanation",
    "TailRiskAllocationResult",
    "TailSetDetails",
    "TechnicalPricingEngine",
    "UnderwritingDecision",
    "VersionMetadata",
    "VulnerabilityCurve",
    "VulnerabilityEngine",
    "VulnerabilityError",
    "VulnerabilityModelError",
    "VulnerabilityResult",
    "WhatIfSensitivityResult",
    "WorkflowExecutionResult",
    "calculate_decision_hash",
    "get_logger",
    "initialize_database",
    "load_config",
    "run_catastrophe_model",
    "run_risk_analytics",
    "setup_logging",
]



