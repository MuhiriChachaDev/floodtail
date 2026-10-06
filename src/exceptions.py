"""FLOODTAIL — Custom exception hierarchy.

All FLOODTAIL-specific exceptions inherit from FloodtailError,
enabling callers to catch the full family or specific subtypes.
"""


class FloodtailError(Exception):
    """Base exception for all FLOODTAIL errors."""


class ConfigurationError(FloodtailError):
    """Raised when configuration loading, parsing, or validation fails.

    Examples:
        - config.yaml is missing
        - A required configuration section is absent
        - A configuration value is out of acceptable range
    """


class SchemaValidationError(FloodtailError):
    """Raised when a data record fails Pydantic schema validation.

    Examples:
        - Latitude outside [-90, 90]
        - Negative insured value
        - Missing required field
    """


class DataQualityError(FloodtailError):
    """Raised when ingested data fails quality checks.

    Examples:
        - Duplicate policy IDs detected
        - Outlier values flagged by quality rules
        - Incomplete batch rejected
    """


class HazardInputError(FloodtailError):
    """Raised when hazard model inputs are invalid.

    Examples:
        - Missing footprint reference
        - Invalid flood depth
        - Unsupported hazard type
    """


class VulnerabilityError(FloodtailError):
    """Raised when vulnerability model inputs or outputs are invalid.

    Examples:
        - Damage ratio outside [0, 1]
        - Unknown construction class
        - Missing vulnerability curve
    """


class ModelCalculationError(FloodtailError):
    """Raised when a model calculation produces an invalid result.

    Examples:
        - Numerical overflow in loss aggregation
        - Division by zero in pricing
        - NaN in tail risk computation
    """


class ReconciliationError(FloodtailError):
    """Raised when pipeline outputs fail internal consistency checks.

    Examples:
        - Sum of policy losses exceeds portfolio total
        - Event counts mismatch between modules
        - Missing records in join operations
    """


class GovernanceError(FloodtailError):
    """Raised when a governance or audit constraint is violated.

    Examples:
        - Human review required but not completed
        - Audit trail incomplete
        - Unauthorized override attempted
    """
