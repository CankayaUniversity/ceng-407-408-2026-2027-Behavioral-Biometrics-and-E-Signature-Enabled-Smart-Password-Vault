class MockFingerprintDevice:
    """Simulates fingerprint enrollment and scans without real hardware."""

    def __init__(self, device_id: str):
        if not device_id.strip():
            raise ValueError("Device ID cannot be empty.")

        self.device_id = device_id
        self.enrolled_users: set[str] = set()

    def enroll(self, user_id: str) -> bool:
        """Register a simulated user in memory."""
        if not user_id.strip():
            raise ValueError("User ID cannot be empty.")

        self.enrolled_users.add(user_id)
        return True

    def verify(self, user_id: str, *, scan_success: bool) -> bool:
        """Return whether an enrolled user's simulated scan succeeds."""
        return user_id in self.enrolled_users and scan_success