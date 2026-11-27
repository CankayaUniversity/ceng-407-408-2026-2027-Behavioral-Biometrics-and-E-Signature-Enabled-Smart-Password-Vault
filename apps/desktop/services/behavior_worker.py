"""Local demo-only worker. No account login, raw keys, or arbitrary paths over IPC."""

import json
import sys

from packages.behavioral_ai.realtime.playback import synthetic_window
from packages.behavioral_ai.realtime.service import MonitoringService, ProfileStore


class BehaviorWorker:
    def __init__(self, directory):
        # Explicit demonstration threshold; NOT calibrated production policy.
        self.service = MonitoringService(ProfileStore(directory), threshold=3.0)
        self.bound = False

    def handle(self, command, data):
        service = self.service
        if command == "logout":
            self.bound = False
            return service.logout()
        if command == "pause":
            return service.pause()
        if command == "delete":
            if not self.bound:
                service.bind("synthetic-demo-user", "synthetic-playback")
                self.bound = True
            return service.delete()
        if command != "play" or not isinstance(data, dict):
            return service.result("invalid_command")
        if data.get("consent") is not True:
            service.logout()
            self.bound = False
            return service.result("consent_required")
        if not self.bound:
            service.bind("synthetic-demo-user", "synthetic-playback")
            self.bound = True
        action = data.get("action")
        if action not in {"enroll-1", "enroll-2", "genuine", "impostor"}:
            return service.result("invalid_command")
        enrolling = action.startswith("enroll")
        index = 1 if action == "enroll-1" else 2 if enrolling else 3
        result = service.start(f"synthetic-session-{index}", "enroll" if enrolling else "verify", consent=True)
        if not service.active:
            return result
        result = service.ingest(synthetic_window(index, impostor=action == "impostor"))
        service.pause()
        if enrolling and result["status"] == "enrollment_recorded" and len(service.vector_sessions) >= 2:
            return service.finish_enrollment()
        return result


def main():
    worker = BehaviorWorker(sys.argv[1])
    for line in sys.stdin:
        try:
            if len(line) > 4096:
                raise ValueError()
            request = json.loads(line)
            result = worker.handle(request.get("command"), request.get("data"))
        except Exception:
            worker.service.pause()
            result = worker.service.result("worker_error")
        print(json.dumps(result, allow_nan=False), flush=True)
    worker.service.logout()


if __name__ == "__main__":
    main()
