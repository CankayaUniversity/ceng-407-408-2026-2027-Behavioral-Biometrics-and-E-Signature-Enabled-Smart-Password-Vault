import argparse
import sys
from base64 import urlsafe_b64encode
from dataclasses import asdict
from uuid import uuid4

import httpx

from packages.device_protocol.fingerprint.models import FingerSlot
from packages.device_protocol.protocol.challenge import AuthenticationChallenge
from packages.device_protocol.simulator.enrollment_service import (
    FingerprintEnrollmentService,
)
from packages.device_protocol.simulator.mock_device import MockFingerprintDevice


def post_json(client, path, payload, *, headers=None):
    response = client.post(path, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def run_demo(client, *, scan_success):
    registration = post_json(client, "/v1/users", {"display_name": "Device Demo"})
    user_id = registration["user_id"]
    device = MockFingerprintDevice(str(uuid4()))
    finger_slot = FingerSlot.RIGHT_INDEX
    enrollment = FingerprintEnrollmentService(device)
    enrollment.enroll_finger(user_id, finger_slot.value)

    public_key = urlsafe_b64encode(device.export_public_key()).decode("ascii").rstrip("=")
    pairing = post_json(
        client,
        "/v1/devices/pair",
        {
            "user_id": user_id,
            "device_id": device.device_id,
            "public_key": public_key,
        },
        headers={"Authorization": f"Bearer {registration['pairing_code']}"},
    )
    print(f"Device paired: {pairing['device_id']} ({pairing['pairing_status']})")

    issuance = post_json(
        client,
        "/v1/auth/challenges",
        {"user_id": user_id, "device_id": device.device_id, "purpose": "login"},
    )
    challenge = AuthenticationChallenge(**issuance["challenge"])
    signed_response = device.respond_to_challenge(
        challenge, finger_slot, scan_success=scan_success
    )
    result = post_json(client, "/v1/auth/verify", asdict(signed_response))

    session = result["session"]
    if session["session_id"] != issuance["session_id"] or session["state"] != "TRUSTED":
        raise RuntimeError("Backend did not confirm the expected trusted session.")

    return session


def main():
    parser = argparse.ArgumentParser(description="Run the local device authentication demo.")
    parser.add_argument("--failed-scan", action="store_true")
    args = parser.parse_args()

    try:
        with httpx.Client(
            base_url="http://127.0.0.1:8000", timeout=5.0, trust_env=False
        ) as client:
            session = run_demo(client, scan_success=not args.failed_scan)
    except httpx.HTTPStatusError as error:
        print(
            f"{error.request.url.path} returned HTTP {error.response.status_code}.",
            file=sys.stderr,
        )
        return 1
    except httpx.RequestError:
        print("Could not reach the local backend at 127.0.0.1:8000.", file=sys.stderr)
        return 1
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1

    print(f"Session {session['session_id']}: {session['state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())