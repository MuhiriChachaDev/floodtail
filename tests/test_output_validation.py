"""Output number-allowlist validation tests (Phase E)."""

from __future__ import annotations

from packages.security.encryption import decrypt_aes_gcm, encrypt_aes_gcm, hash_token
from packages.security.output_validation import (
    numbers_in_allowlist,
    reject_invented_kes,
    validate_insight_fields,
)


def test_allowlist_accepts_known_numbers() -> None:
    allow = {
        "total_tiv_kes": 1_000_000.0,
        "set_aside_floor_kes": 250_000.5,
        "aal_kes": 12_345.0,
    }
    text = "TIV is KES 1,000,000 and floor KES 250000.5 with AAL KES 12345"
    ok, invented = numbers_in_allowlist(text, allow)
    assert ok
    assert invented == []


def test_rejects_invented_kes() -> None:
    allow = {"total_tiv_kes": 1000.0, "aal_kes": 10.0}
    err = reject_invented_kes("Loss is KES 999999999", allow)
    assert err is not None
    ok, errs = validate_insight_fields(
        narrative="Set aside KES 888888888",
        why=["houses look fine"],
        next_steps=["review"],
        allowlist=allow,
    )
    assert not ok
    assert errs


def test_aes_gcm_roundtrip_and_hash_token() -> None:
    # 32-byte key base64 (settings-style)
    import base64

    key = base64.b64encode(b"0123456789abcdef0123456789abcdef").decode()
    token = encrypt_aes_gcm("owner@example.com", key)
    assert decrypt_aes_gcm(token, key) == "owner@example.com"
    h1 = hash_token("owner@example.com")
    h2 = hash_token("owner@example.com")
    assert h1 == h2
    assert h1 != hash_token("other@example.com")
    assert len(h1) == 32
