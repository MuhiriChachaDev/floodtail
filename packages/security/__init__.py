"""kenyaRE-style security: RBAC, prompt defence, encryption, audit, tenant."""

from packages.security.audit_log import AuditChain, get_audit_chain, reset_audit_chain
from packages.security.encryption import decrypt_aes_gcm, encrypt_aes_gcm, hash_token
from packages.security.output_validation import (
    numbers_in_allowlist,
    reject_invented_kes,
    validate_insight_fields,
)
from packages.security.prompt_defence import (
    SAFE_SYSTEM_PROMPT,
    defend_user_text,
    detect_injection,
    wrap_as_data,
)
from packages.security.rbac import ForbiddenError, has_permission, require_permission
from packages.security.tenant import TenantMismatchError, assert_same_tenant

__all__ = [
    "AuditChain",
    "ForbiddenError",
    "SAFE_SYSTEM_PROMPT",
    "TenantMismatchError",
    "assert_same_tenant",
    "decrypt_aes_gcm",
    "defend_user_text",
    "detect_injection",
    "encrypt_aes_gcm",
    "get_audit_chain",
    "has_permission",
    "hash_token",
    "numbers_in_allowlist",
    "reject_invented_kes",
    "require_permission",
    "reset_audit_chain",
    "validate_insight_fields",
    "wrap_as_data",
]
