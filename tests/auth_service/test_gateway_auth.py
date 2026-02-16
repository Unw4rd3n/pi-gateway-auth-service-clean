import pytest
from fastapi import HTTPException

from services.gateway.app.security import decode_access_token
from services.auth_service.app.security import create_access_token


def test_gateway_rejects_missing_token():
    with pytest.raises(HTTPException) as exc:
        decode_access_token(None)

    assert exc.value.status_code == 401


def test_gateway_accepts_valid_access_token():
    token = create_access_token("user-42", role="user")
    payload = decode_access_token(f"Bearer {token}")

    assert payload["sub"] == "user-42"
    assert payload["type"] == "access"
