import json
from pathlib import Path

import pytest

from services.backend.app.schemas.auth import (
    AuthChallengeCreateResponse,
    AuthVerifyResponse,
)
from services.backend.app.schemas.device import DevicePairResponse
from services.backend.app.schemas.error import ErrorResponse
from services.backend.app.schemas.session import SessionResponse
from services.backend.app.schemas.user import UserRegistrationResponse


EXAMPLES_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "examples"
    / "auth_responses.json"
)


@pytest.mark.parametrize(
    "example_name, schema",
    [
        ("user_created", UserRegistrationResponse),
        ("device_pairing", DevicePairResponse),
        ("challenge_created", AuthChallengeCreateResponse),
        ("authentication_verified", AuthVerifyResponse),
        ("session_revoked", SessionResponse),
        ("authentication_error", ErrorResponse),
    ],
)
def test_mock_response_matches_schema(example_name, schema):
    examples = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))

    schema.model_validate(examples[example_name])


def test_session_read_example_matches_schema():
    examples = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))

    SessionResponse.model_validate(
        examples["authentication_verified"]["session"]
    )