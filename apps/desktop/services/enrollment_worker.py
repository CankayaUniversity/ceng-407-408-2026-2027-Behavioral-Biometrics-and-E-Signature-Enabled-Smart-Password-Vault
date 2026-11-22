"""Private, line-delimited JSON bridge for the local Electron enrollment UI.

One worker owns one enrollment attempt. Keys and pairing credentials never leave
this process. Devices are intentionally memory-only until the application exits.
"""

import json
import sys
from base64 import urlsafe_b64encode
from datetime import datetime, timezone

import httpx

from packages.device_protocol.fingerprint.models import FingerSlot
from packages.device_protocol.simulator.enrollment_service import FingerprintEnrollmentService
from packages.device_protocol.simulator.mock_device import MockFingerprintDevice


class EnrollmentWorker:
    def __init__(self, client):
        self.client = client
        self.device = None
        self.registration = None
        self.slot = None
        self.enrolled = False
        self.paired = False
        self.uncertain = False
        self.started = False

    def snapshot(self):
        user = self.registration
        return {
            "userId": user["user_id"] if user else None,
            "deviceId": self.device.device_id if self.device else None,
            "fingerSlot": self.slot.value if self.slot else None,
            "registered": user is not None,
            "enrolled": self.enrolled,
            "paired": self.paired,
            "pairingStatus": "PENDING" if self.paired else None,
            "uncertain": self.uncertain,
        }

    def result(self, code=None, retryable=False):
        return {"snapshot": self.snapshot(), "error": code, "retryable": retryable}

    def post(self, path, payload, headers=None):
        try:
            response = self.client.post(path, json=payload, headers=headers)
        except httpx.ConnectError:
            return None, self.result("DISCONNECTED", retryable=self.registration is not None)
        except httpx.RequestError:
            # A timed-out write may already have committed. Never repeat it blindly.
            self.uncertain = True
            return None, self.result("OUTCOME_UNKNOWN")
        if response.status_code != 201:
            codes = {401: "PAIRING_EXPIRED", 409: "DEVICE_ALREADY_REGISTERED", 422: "VALIDATION_ERROR"}
            code = codes.get(response.status_code, "OUTCOME_UNKNOWN")
            if code == "OUTCOME_UNKNOWN":
                self.uncertain = True
            return None, self.result(code)
        try:
            data = response.json()
            if path == "/v1/users":
                for key in ("user_id", "pairing_code", "pairing_code_expires_at"):
                    if not isinstance(data[key], str) or not data[key]:
                        raise ValueError()
                expiry = datetime.fromisoformat(data["pairing_code_expires_at"].replace("Z", "+00:00"))
                if expiry.tzinfo is None:
                    raise ValueError()
            elif data["user_id"] != self.registration["user_id"] or data["device_id"] != self.device.device_id or data["pairing_status"] != "PENDING":
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            self.uncertain = True
            return None, self.result("OUTCOME_UNKNOWN")
        return data, None

    def register(self, data):
        if self.started:
            return self.result("ALREADY_STARTED")
        name = data.get("displayName", "")
        device_id = data.get("deviceId", "")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
            return self.result("VALIDATION_ERROR")
        if not isinstance(device_id, str) or not 1 <= len(device_id.strip()) <= 36:
            return self.result("VALIDATION_ERROR")
        try:
            self.slot = FingerSlot(data.get("fingerSlot"))
        except (ValueError, TypeError):
            return self.result("VALIDATION_ERROR")
        self.device = MockFingerprintDevice(device_id.strip())
        self.started = True
        user, error = self.post("/v1/users", {"display_name": name.strip()})
        if error:
            return error
        self.registration = user
        return self.result()

    def complete(self):
        if not self.registration or self.uncertain:
            return self.result("OUTCOME_UNKNOWN" if self.uncertain else "NOT_REGISTERED")
        if self.paired:
            return self.result()
        expiry = datetime.fromisoformat(self.registration["pairing_code_expires_at"].replace("Z", "+00:00"))
        if expiry <= datetime.now(timezone.utc):
            return self.result("PAIRING_EXPIRED")
        if not self.enrolled:
            self.enrolled = FingerprintEnrollmentService(self.device).enroll_finger(
                self.registration["user_id"], self.slot.value
            )
            if not self.enrolled:
                return self.result("DEVICE_REJECTED", retryable=True)
        public_key = urlsafe_b64encode(self.device.export_public_key()).decode("ascii").rstrip("=")
        _, error = self.post("/v1/devices/pair", {
            "user_id": self.registration["user_id"],
            "device_id": self.device.device_id,
            "public_key": public_key,
        }, {"Authorization": f"Bearer {self.registration['pairing_code']}"})
        if error:
            return error
        self.paired = True
        self.registration.pop("pairing_code", None)
        return self.result()


def main():
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=8.0, trust_env=False, follow_redirects=False) as client:
        worker = EnrollmentWorker(client)
        for line in sys.stdin:
            try:
                request = json.loads(line)
                command = request.get("command")
                if command == "register":
                    result = worker.register(request.get("data", {}))
                elif command == "complete":
                    result = worker.complete()
                else:
                    result = worker.result("INVALID_COMMAND")
            except Exception:
                # Never serialize exception strings: HTTP errors can contain secrets.
                worker.uncertain = True
                result = worker.result("OUTCOME_UNKNOWN")
            print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
