from services.auth_service.app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    raw = "super-secret-pass"
    hashed = hash_password(raw)

    assert hashed != raw
    assert verify_password(raw, hashed)


def test_access_token_has_expected_claims():
    token = create_access_token("user-1", role="admin")
    payload = decode_token(token)

    assert payload["sub"] == "user-1"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
    assert "jti" in payload


def test_refresh_token_has_expected_claims():
    token = create_refresh_token("user-2", role="user")
    payload = decode_token(token)

    assert payload["sub"] == "user-2"
    assert payload["role"] == "user"
    assert payload["type"] == "refresh"
