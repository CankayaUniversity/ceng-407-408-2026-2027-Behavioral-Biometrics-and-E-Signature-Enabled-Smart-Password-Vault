from pathlib import Path
from typing import Any

import yaml

from services.backend.app.schemas.auth import (
    AuthChallengeCreateRequest,
    AuthChallengeCreateResponse,
    AuthVerifyRequest,
    AuthVerifyResponse,
)
from services.backend.app.schemas.device import DevicePairRequest, DevicePairResponse
from services.backend.app.schemas.error import ErrorResponse
from services.backend.app.schemas.session import SessionResponse
from services.backend.app.schemas.user import (
    UserCreateRequest,
    UserRegistrationResponse,
)


MODELS = [
    UserCreateRequest,
    UserRegistrationResponse,
    DevicePairRequest,
    DevicePairResponse,
    AuthChallengeCreateRequest,
    AuthChallengeCreateResponse,
    AuthVerifyRequest,
    AuthVerifyResponse,
    SessionResponse,
    ErrorResponse,
]

DRAFT_ERRORS = {
    "401": "UNAUTHORIZED: required credentials are missing, invalid, or expired.",
    "403": (
        "FORBIDDEN: the caller lacks permission or the session state "
        "disallows the operation."
    ),
    "422": "VALIDATION_ERROR: request fields or cross-field constraints are invalid.",
    "429": "RATE_LIMITED: request or authentication attempt limit exceeded.",
    "500": "INTERNAL_ERROR: unexpected server failure.",
}

NOT_FOUND = "NOT_FOUND: an authorized resource lookup found no matching resource."


def json_content(model):
    return {
        "application/json": {
            "schema": {"$ref": f"#/components/schemas/{model.__name__}"},
        },
    }


def operation(
    summary, response_model, success_status, errors, request_model=None
) -> dict[str, Any]:
    responses: dict[str, dict[str, Any]] = {
        success_status: {
            "description": "Successful response",
            "content": json_content(response_model),
        },
    }

    for status_code, description in errors.items():
        response: dict[str, Any] = {
            "description": description,
            "content": json_content(ErrorResponse),
        }
        if status_code == "401":
            response["headers"] = {
                "WWW-Authenticate": {
                    "description": "Authentication challenge.",
                    "schema": {"type": "string"},
                },
            }
        responses[status_code] = response

    result: dict[str, Any] = {"summary": summary, "responses": responses}

    if request_model is not None:
        result["requestBody"] = {
            "required": True,
            "content": json_content(request_model),
        }

    return result


def main():
    schemas: dict[str, Any] = {}
    for model in MODELS:
        schema = model.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        schemas.update(schema.pop("$defs", {}))
        schemas[model.__name__] = schema

    register_user = operation(
        "Create a user and issue a single-use pairing code",
        UserRegistrationResponse,
        "201",
        {
            "422": "VALIDATION_ERROR: invalid registration request.",
            "500": "INTERNAL_ERROR: unable to create user.",
        },
        UserCreateRequest,
    )
    register_user["description"] = (
        "The pairing code belongs to the newly created user and expires "
        "five minutes after issuance."
    )
    register_user["responses"]["201"]["headers"] = {
        "Cache-Control": {
            "description": "Prevents caching of the pairing credential.",
            "schema": {"type": "string", "const": "no-store"},
        },
    }

    pair_device = operation(
        "Register a pending device using a pairing code",
        DevicePairResponse,
        "201",
        {
            "401": (
                "UNAUTHORIZED: pairing code is missing, invalid, expired, "
                "already used, or issued for a different user."
            ),
            "409": "DEVICE_ALREADY_REGISTERED: the device ID already exists.",
            "422": "VALIDATION_ERROR: invalid request fields or public key encoding.",
            "500": "INTERNAL_ERROR: unable to register device.",
        },
        DevicePairRequest,
    )
    pair_device["security"] = [{"PairingCode": []}]
    pair_device["description"] = (
        "Send the registration pairing code in the Authorization bearer header. "
        "The public key must be 32 raw Ed25519 bytes encoded as unpadded "
        "Base64url. A successful registration consumes the code and creates "
        "a PENDING device record in the same transaction."
    )
    pair_device["responses"]["401"]["headers"]["WWW-Authenticate"]["schema"] = {
        "type": "string",
        "const": "Bearer",
    }

    verification_errors = {
        **DRAFT_ERRORS,
        "400": "INVALID_CHALLENGE: the referenced challenge is unknown.",
        "401": (
            DRAFT_ERRORS["401"]
            + " Device verification may also return EXPIRED_CHALLENGE, "
            "INVALID_SIGNATURE, DEVICE_MISMATCH, REQUEST_MISMATCH, "
            "or VERIFICATION_FAILED."
        ),
        "409": "REPLAY_DETECTED: the challenge was already consumed.",
    }

    paths: dict[str, dict[str, Any]] = {
        "/v1/users": {"post": register_user},
        "/v1/devices/pair": {"post": pair_device},
        "/v1/auth/challenges": {
            "post": operation(
                "Create an authentication challenge (draft)",
                AuthChallengeCreateResponse,
                "201",
                DRAFT_ERRORS,
                AuthChallengeCreateRequest,
            ),
        },
        "/v1/auth/verify": {
            "post": operation(
                "Submit a signed device response (draft)",
                AuthVerifyResponse,
                "200",
                verification_errors,
                AuthVerifyRequest,
            ),
        },
        "/v1/sessions/{session_id}": {
            "get": operation(
                "Read an authorized session (draft)",
                SessionResponse,
                "200",
                {**DRAFT_ERRORS, "404": NOT_FOUND},
            ),
        },
        "/v1/sessions/{session_id}/revoke": {
            "post": operation(
                "Revoke an authorized session (draft)",
                SessionResponse,
                "200",
                {**DRAFT_ERRORS, "404": NOT_FOUND},
            ),
        },
    }

    for path, path_item in paths.items():
        if "{session_id}" in path:
            path_item["parameters"] = [
                {
                    "name": "session_id",
                    "in": "path",
                    "required": True,
                    "schema": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 36,
                    },
                },
            ]

    document = {
        "openapi": "3.1.0",
        "info": {
            "title": "Authentication API",
            "version": "0.1.0",
            "description": (
                "User registration and device pairing are implemented in BE-05. "
                "Challenge, verification, and session operations are draft contracts. "
                "Missing security declarations do not imply public access. "
                "Response timestamps must be normalized to UTC. "
                "Device signatures cover version, challenge_id, device_id, "
                "and payload. Session binding is resolved from the stored challenge. "
                "See auth_api.md and device_protocol.md."
            ),
        },
        "paths": paths,
        "components": {
            "schemas": schemas,
            "securitySchemes": {
                "PairingCode": {"type": "http", "scheme": "bearer"},
            },
        },
    }

    project_root = Path(__file__).resolve().parents[1]
    output = project_root / "contracts" / "auth.openapi.yaml"
    output.write_text(
        yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"OpenAPI specification generated: {output}")


if __name__ == "__main__":
    main()