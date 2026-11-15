import pytest
from pydantic import ValidationError

from services.backend.app.schemas.auth import (
    AuthChallengeCreateRequest,
    AuthChallengeResponse,
    AuthVerifyRequest,
)
from services.backend.app.schemas.user import UserCreateRequest


def make_device_response():
    return {
        "version": 1,
        "challenge_id": "example-challenge",
        "device_id": "example-device",
        "payload": {
            "request_id": "example-request",
            "user_id": "example-user",
            "purpose": "login",
            "nonce": "example-nonce",
            "verified": True,
        },
        "signature": "example-signature",
    }


def test_user_name_is_trimmed():
    request = UserCreateRequest(display_name=" Kaan ")

    assert request.display_name == "Kaan"


@pytest.mark.parametrize("display_name", ["", "   ", "a" * 101])
def test_invalid_user_name_rejected(display_name):
    with pytest.raises(ValidationError):
        UserCreateRequest(display_name=display_name)


@pytest.mark.parametrize(
    "purpose, session_id",
    [
        ("login", None),
        ("reauthentication", "example-session"),
    ],
)
def test_valid_challenge_context(purpose, session_id):
    request = AuthChallengeCreateRequest(
        user_id="example-user",
        device_id="example-device",
        purpose=purpose,
        session_id=session_id,
    )

    assert request.purpose == purpose
    assert request.session_id == session_id


@pytest.mark.parametrize(
    "purpose, session_id",
    [
        ("login", "example-session"),
        ("reauthentication", None),
    ],
)
def test_invalid_challenge_context_rejected(purpose, session_id):
    with pytest.raises(ValidationError):
        AuthChallengeCreateRequest(
            user_id="example-user",
            device_id="example-device",
            purpose=purpose,
            session_id=session_id,
        )


@pytest.mark.parametrize("verified", [True, False])
def test_boolean_verification_result_accepted(verified):
    data = make_device_response()
    data["payload"]["verified"] = verified

    request = AuthVerifyRequest.model_validate(data)

    assert request.payload.verified is verified


@pytest.mark.parametrize("verified", ["true", "false", 1, 0])
def test_non_boolean_verification_result_rejected(verified):
    data = make_device_response()
    data["payload"]["verified"] = verified

    with pytest.raises(ValidationError):
        AuthVerifyRequest.model_validate(data)


@pytest.mark.parametrize("version", [True, "1", 1.0, 2])
def test_invalid_protocol_version_rejected(version):
    data = make_device_response()
    data["version"] = version

    with pytest.raises(ValidationError):
        AuthVerifyRequest.model_validate(data)


@pytest.mark.parametrize("location", ["response", "payload"])
def test_unknown_fields_rejected(location):
    data = make_device_response()

    if location == "response":
        data["unexpected"] = "value"
    else:
        data["payload"]["unexpected"] = "value"

    with pytest.raises(ValidationError):
        AuthVerifyRequest.model_validate(data)


def test_signed_strings_are_not_trimmed():
    data = make_device_response()
    data["payload"]["request_id"] = " example-request "

    request = AuthVerifyRequest.model_validate(data)

    assert request.payload.request_id == " example-request "


@pytest.mark.parametrize(
    "expires_at, accepted",
    [
        ("2026-11-15T12:00:00Z", True),
        ("2026-11-15T12:00:00", False),
    ],
)
def test_challenge_requires_timezone(expires_at, accepted):
    data = {
        "version": 1,
        "challenge_id": "example-challenge",
        "request_id": "example-request",
        "user_id": "example-user",
        "device_id": "example-device",
        "purpose": "login",
        "nonce": "example-nonce",
        "expires_at": expires_at,
    }

    if accepted:
        assert AuthChallengeResponse.model_validate(data).expires_at.tzinfo
    else:
        with pytest.raises(ValidationError):
            AuthChallengeResponse.model_validate(data)

@pytest.mark.parametrize(
    "model_name, field",
    [
        ("user", "created_at"),
        ("session", "created_at"),
        ("session", "expires_at"),
        ("session", "revoked_at"),
        ("session", "last_reauth_at"),
    ],
)
@pytest.mark.parametrize(
    "timestamp, accepted",
    [
        ("2026-11-15T12:00:00Z", True),
        ("2026-11-15T15:00:00+03:00", True),
        ("2026-11-15T12:00:00", False),
    ],
)
def test_response_timestamps_require_timezone(
    model_name, field, timestamp, accepted
):
    from services.backend.app.schemas.session import SessionResponse
    from services.backend.app.schemas.user import UserCreateResponse

    if model_name == "user":
        schema = UserCreateResponse
        data = {
            "user_id": "example-user",
            "display_name": "Example User",
            "enrollment_status": "PENDING",
            "created_at": "2026-11-15T12:00:00Z",
        }
    else:
        schema = SessionResponse
        data = {
            "session_id": "example-session",
            "user_id": "example-user",
            "state": "LOCKED",
            "created_at": "2026-11-15T12:00:00Z",
            "expires_at": "2026-11-15T13:00:00Z",
        }

    data[field] = timestamp

    if accepted:
        result = schema.model_validate(data)
        assert getattr(result, field).tzinfo is not None
    else:
        with pytest.raises(ValidationError):
            schema.model_validate(data)