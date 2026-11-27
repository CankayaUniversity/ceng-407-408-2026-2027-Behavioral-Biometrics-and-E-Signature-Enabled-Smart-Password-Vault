"""Bounded, session-aware enrollment and claimed-user verification."""

from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

from packages.behavioral_ai.features import FEATURE_VERSION, WINDOW_SIZE, extract_window, feature_vector
from packages.behavioral_ai.features.extractor import validate_samples
from packages.behavioral_ai.models.profile import UserProfile, validate_vector
from packages.behavioral_ai.inference.verifier import verify_window

MODEL_VERSION = "standardized-rms-v1"

FIELDS = {"dwell_ms", "down_down_ms", "flight_ms"}


class ProfileStore:
    """Private atomic profile storage. Raw samples are never written."""

    def __init__(self, directory):
        self.directory = Path(directory)

    def path(self, user):
        return self.directory / (hashlib.sha256(user.encode()).hexdigest() + ".json")

    def save(self, profile, sessions, source):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=self.directory,
                                             prefix=f".{self.path(profile.user_id).stem}.",
                                             suffix=".tmp", delete=False) as file:
                name = file.name
                json.dump({"schema_version": 1, "model_version": MODEL_VERSION, "profile": asdict(profile),
                           "sessions": sorted(sessions), "source": source}, file, allow_nan=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(name, self.path(profile.user_id))
        finally:
            if name:
                Path(name).unlink(missing_ok=True)

    def load(self, user, source):
        try:
            data = json.loads(self.path(user).read_text())
        except FileNotFoundError:
            return None, set()
        if data["schema_version"] != 1 or data["model_version"] != MODEL_VERSION or data["source"] != source:
            raise ValueError("Incompatible profile")
        profile = UserProfile(**data["profile"])
        if profile.user_id != user or profile.feature_version != FEATURE_VERSION:
            raise ValueError("Incompatible profile")
        sessions = data["sessions"]
        if not isinstance(sessions, list) or not all(isinstance(s, str) and s for s in sessions) or len(set(sessions)) < 2:
            raise ValueError("Invalid enrollment provenance")
        return profile, set(sessions)

    def delete(self, user):
        self.path(user).unlink(missing_ok=True)
        # Remove this user's interrupted atomic writes as well, after worker stop.
        for temporary in self.directory.glob(f".{self.path(user).stem}.*.tmp"):
            temporary.unlink(missing_ok=True)


class MonitoringService:
    """One local claimed-user context; caller must supply trusted auth for live use.

    A source namespace prevents synthetic/public profiles becoming live profiles.
    Enrollment retains feature vectors only, with at most 32 windows / 16 sessions.
    """

    def __init__(self, store, *, threshold):
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or threshold < 0:
            raise ValueError("Invalid explicit threshold")
        self.store = store
        self.threshold = threshold
        self.user = None
        self.source = None
        self.profile = None
        self.enrollment_sessions = set()
        self.vectors = []
        self.vector_sessions = set()
        self.active = False
        self.samples = []
        self.mode = None
        self.session = None

    def result(self, status, *, verification=None, quality=None):
        return {"schema_version": 1, "feature_version": FEATURE_VERSION,
                "window_size": WINDOW_SIZE, "source": self.source,
                "model_version": MODEL_VERSION,
                "score_semantics": "lower_distance_is_closer_uncalibrated",
                "status": status, "model_ready": self.profile is not None,
                "buffered_samples": len(self.samples),
                "enrollment_windows": len(self.vectors),
                "enrollment_sessions": len(self.vector_sessions),
                "verification": verification, "quality": quality}

    def bind(self, user, source):
        self.logout()
        if not isinstance(user, str) or not user.strip() or len(user) > 128:
            raise ValueError("Invalid claimed user")
        if source not in {"scoped-input", "synthetic-playback", "keyrecs-free"}:
            raise ValueError("Invalid source")
        self.user, self.source = user, source
        try:
            self.profile, self.enrollment_sessions = self.store.load(user, source)
        except (ValueError, KeyError, TypeError, OSError):
            return self.result("profile_unavailable")
        return self.result("ready" if self.profile else "model_not_ready")

    def start(self, session, mode, *, consent, permitted=True):
        self.pause()
        if consent is not True:
            return self.result("consent_required")
        if permitted is not True:
            return self.result("permission_denied")
        if not self.user:
            return self.result("no_context")
        if not isinstance(session, str) or not session or len(session) > 128 or mode not in {"enroll", "verify"}:
            raise ValueError("Invalid recording context")
        if mode == "verify" and session in self.enrollment_sessions | self.vector_sessions:
            return self.result("enrollment_session_reuse")
        if mode == "verify" and self.profile is None:
            return self.result("model_not_ready")
        self.session, self.mode, self.active = session, mode, True
        return self.result("insufficient_data")

    def ingest(self, samples):
        if not self.active:
            return self.result("paused")
        try:
            if not isinstance(samples, list) or len(samples) > WINDOW_SIZE:
                raise ValueError("Bound exceeded")
            if any(not isinstance(s, dict) or set(s) != FIELDS for s in samples):
                raise ValueError("Only timing fields accepted")
            validate_samples(samples)
            if len(self.samples) + len(samples) > WINDOW_SIZE:
                raise ValueError("Window overflow")
        except (TypeError, ValueError):
            self.pause()
            return self.result("invalid_samples")
        self.samples.extend(dict(sample) for sample in samples)
        if len(self.samples) < WINDOW_SIZE:
            return self.result("insufficient_data")
        window, self.samples = self.samples, []
        try:
            features = extract_window(window)
            if features is not None:
                validate_vector(feature_vector(features))
        except (ValueError, OverflowError):
            self.pause()
            return self.result("invalid_features")
        if features is None:
            return self.result("insufficient_coverage")
        quality = {name: features[name] for name in
                   ("down_down_coverage", "flight_coverage", "down_down_count", "flight_count")}
        if self.mode == "enroll":
            if len(self.vectors) >= 32 or (self.session not in self.vector_sessions and len(self.vector_sessions) >= 16):
                self.pause()
                return self.result("enrollment_limit")
            self.vectors.append(feature_vector(features))
            self.vector_sessions.add(self.session)
            return self.result("enrollment_recorded", quality=quality)
        result = verify_window(self.user, window, self.profile, threshold=self.threshold)
        # Do not emit nonfinite scores, user IDs, vectors, samples or exception text.
        if result.distance is not None and not math.isfinite(result.distance):
            return self.result("invalid_score")
        return self.result("verified", verification=asdict(result), quality=quality)

    def finish_enrollment(self):
        self.pause()
        if not self.user or len(self.vector_sessions) < 2 or len(self.vectors) < 2:
            return self.result("insufficient_enrollment")
        profile = UserProfile.fit(self.user, self.vectors)
        self.store.save(profile, self.vector_sessions, self.source)
        self.profile = profile
        self.enrollment_sessions = set(self.vector_sessions)
        self.vectors.clear()
        self.vector_sessions.clear()
        return self.result("ready")

    def pause(self):
        self.active = False
        self.samples.clear()
        self.mode = self.session = None
        return self.result("paused")

    def logout(self):
        self.pause()
        self.vectors.clear()
        self.vector_sessions.clear()
        self.enrollment_sessions.clear()
        self.user = self.source = self.profile = None
        return self.result("stopped")

    def delete(self):
        self.pause()
        if self.user:
            self.store.delete(self.user)
        self.profile = None
        self.vectors.clear()
        self.vector_sessions.clear()
        self.enrollment_sessions.clear()
        return self.result("deleted")
