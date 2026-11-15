from pathlib import Path

import yaml

from services.backend.app.schemas.auth import (
    AuthChallengeCreateRequest,
    AuthChallengeCreateResponse,
    AuthVerifyRequest,
    AuthVerifyResponse,
)
from services.backend.app.schemas.device import (
    DevicePairRequest,
    DevicePairResponse,
)
from services.backend.app.schemas.error import ErrorResponse
from services.backend.app.schemas.session import SessionResponse
from services.backend.app.schemas.user import (
    UserCreateRequest,
    UserCreateResponse,
)


MODELS = [
    UserCreateRequest,
    UserCreateResponse,
    DevicePairRequest,
    DevicePairResponse,
    AuthChallengeCreateRequest,
    AuthChallengeCreateResponse,
    AuthVerifyRequest,
    AuthVerifyResponse,
    SessionResponse,
    ErrorResponse,
]


def schema_ref(model):
    return {"$ref": f"#/components/schemas/{model.__name__}"}


def operation(summary, response_model, status, request_model=None):
    result = {
        "summary": summary,
        "description": (
            "Draft contract only; this endpoint is not implemented by "
            "the exporter. Authorization and policy require team review."
        ),
        "responses": {
            str(status): {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": schema_ref(response_model),
                    },
                },
            },
            "default": {
                "description": (
                    "Error response. See auth_api.md for proposed "
                    "HTTP status and error code mappings."
                ),
                "content": {
                    "application/json": {
                        "schema": schema_ref(ErrorResponse),
                    },
                },
            },
        },
    }

    if request_model is not None:
        result["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": schema_ref(request_model),
                },
            },
        }

    return result


def main():
    schemas = {}

    for model in MODELS:
        schema = model.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        schemas.update(schema.pop("$defs", {}))
        schemas[model.__name__] = schema

    paths = {
        "/v1/users": {
            "post": operation(
                "Create a user",
                UserCreateResponse,
                201,
                UserCreateRequest,
            ),
        },
        "/v1/devices/pair": {
            "post": operation(
                "Pair a device through an authorized flow",
                DevicePairResponse,
                201,
                DevicePairRequest,
            ),
        },
        "/v1/auth/challenges": {
            "post": operation(
                "Create an authentication challenge",
                AuthChallengeCreateResponse,
                201,
                AuthChallengeCreateRequest,
            ),
        },
        "/v1/auth/verify": {
            "post": operation(
                "Submit a signed device response",
                AuthVerifyResponse,
                200,
                AuthVerifyRequest,
            ),
        },
        "/v1/sessions/{session_id}": {
            "get": operation(
                "Read an authorized session",
                SessionResponse,
                200,
            ),
        },
        "/v1/sessions/{session_id}/revoke": {
            "post": operation(
                "Revoke an authorized session",
                SessionResponse,
                200,
            ),
        },
    }

    error_descriptions = {
        "400": "INVALID_CHALLENGE: the referenced challenge is unknown.",
        "401": (
            "UNAUTHORIZED: missing, invalid, or expired credentials."
        ),
        "403": (
            "FORBIDDEN: the authenticated caller lacks permission, "
            "ownership, or an allowed session state."
        ),
        "404": (
            "NOT_FOUND: an authorized resource lookup finds no resource."
        ),
        "422": (
            "VALIDATION_ERROR: invalid fields, types, required values, "
            "or cross-field constraints."
        ),
        "429": (
            "RATE_LIMITED: request or authentication attempt limit exceeded."
        ),
        "500": "INTERNAL_ERROR: unexpected server failure.",
    }

    for path, path_item in paths.items():
        statuses = {"401", "403", "422", "429", "500"}

        if path == "/v1/auth/verify":
            statuses.update({"400", "409"})

        if path == "/v1/devices/pair":
            statuses.update({"404", "409"})

        if path.startswith("/v1/sessions/"):
            statuses.add("404")

        for endpoint in path_item.values():
            for status in sorted(statuses):
                if status == "409":
                    description = (
                        "DEVICE_ALREADY_REGISTERED: pairing conflicts "
                        "with an existing device registration."
                        if path == "/v1/devices/pair"
                        else "REPLAY_DETECTED: challenge already finalized "
                        "or atomic consumption loses a race."
                    )
                else:
                    description = error_descriptions[status]

                if status == "401" and path == "/v1/auth/verify":
                    description += (
                        " Device verification failures: "
                        "EXPIRED_CHALLENGE (stored challenge expired), "
                        "INVALID_SIGNATURE (signature verification failed), "
                        "DEVICE_MISMATCH (unexpected device), "
                        "REQUEST_MISMATCH (signed context differs from "
                        "the stored challenge), or "
                        "VERIFICATION_FAILED (signed verified=false). "
                        "Detailed conditions and disclosure rules "
                        "are defined in auth_api.md."
                    )

                response = {
                    "description": description,
                    "content": {
                        "application/json": {
                            "schema": schema_ref(ErrorResponse),
                        },
                    },
                }

                if status == "401":
                    response["headers"] = {
                        "WWW-Authenticate": {
                            "description": (
                                "Required authentication challenge; "
                                "scheme and values pending team review."
                            ),
                            "schema": {"type": "string"},
                        },
                    }

                endpoint["responses"][status] = response

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
                "Draft BE-03 contract. Endpoints are not implemented "
                "by this specification. Authentication credentials, "
                "pairing bootstrap, and policies require team review. "
                "Missing security declarations do not imply public access. "
                "Timestamp schemas require explicit timezones; backend "
                "responses must be normalized to UTC. "
                "Device signatures cover version, challenge_id, device_id, "
                "and payload. Session binding is resolved from the "
                "authoritative stored challenge. See auth_api.md "
                "and device_protocol.md."
            ),
        },
        "paths": paths,
        "components": {"schemas": schemas},
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