import json
import os
from dataclasses import replace

import pytest

from apps.desktop.services.behavior_worker import BehaviorWorker
from packages.behavioral_ai.features import FEATURE_VERSION, extract_window
from packages.behavioral_ai.realtime.playback import synthetic_window
from packages.behavioral_ai.realtime.service import MonitoringService, ProfileStore


@pytest.fixture
def service(tmp_path):
    engine = MonitoringService(ProfileStore(tmp_path), threshold=3)
    engine.bind("claimed", "synthetic-playback")
    return engine


def enroll(service):
    for session in (1, 2):
        service.start(str(session), "enroll", consent=True)
        assert service.ingest(synthetic_window(session))["status"] == "enrollment_recorded"
    assert service.finish_enrollment()["status"] == "ready"


def test_consent_permission_and_unenrolled_never_accept(service):
    assert service.start("1", "enroll", consent=False)["status"] == "consent_required"
    assert service.ingest(synthetic_window(1))["verification"] is None
    assert service.start("1", "enroll", consent=True, permitted=False)["status"] == "permission_denied"
    assert service.start("3", "verify", consent=True)["status"] == "model_not_ready"
    assert not service.active


def test_two_sessions_required_and_no_cross_session_window(service):
    service.start("one", "enroll", consent=True)
    service.ingest(synthetic_window(1))
    service.ingest(synthetic_window(2))
    assert service.finish_enrollment()["status"] == "insufficient_enrollment"
    service.start("two", "enroll", consent=True)
    service.ingest(synthetic_window(2)[:99])
    service.start("three", "enroll", consent=True)
    assert service.ingest(synthetic_window(3)[:1])["status"] == "insufficient_data"
    assert len(service.samples) == 1


def test_profile_reload_parity_and_genuine_impostor(service):
    enroll(service)
    assert service.start("1", "verify", consent=True)["status"] == "enrollment_session_reuse"
    for impostor in (False, True):
        service.start("holdout", "verify", consent=True)
        window = synthetic_window(3, impostor=impostor)
        result = service.ingest(window)
        assert result["verification"]["accepted"] is (not impostor)
        assert result["feature_version"] == FEATURE_VERSION
        assert result["quality"]["flight_coverage"] == extract_window(window)["flight_coverage"]
        assert not service.samples
    second = MonitoringService(service.store, threshold=3)
    assert second.bind("claimed", "synthetic-playback")["model_ready"]
    assert second.start("2", "verify", consent=True)["status"] == "enrollment_session_reuse"
    assert not second.bind("other", "synthetic-playback")["model_ready"]
    assert not second.bind("claimed", "scoped-input")["model_ready"]


def test_pause_logout_delete_and_sanitized_disk(service):
    enroll(service)
    stored = service.store.path("claimed").read_text()
    assert "samples" not in stored and "dwell_ms" not in stored
    if os.name != "nt":
        assert service.store.path("claimed").stat().st_mode & 0o777 == 0o600
    service.start("holdout", "verify", consent=True)
    service.ingest(synthetic_window(3)[:99])
    assert service.pause()["buffered_samples"] == 0
    assert service.ingest(synthetic_window(3))["verification"] is None
    service.logout()
    assert service.user is None and not service.vectors and service.profile is None
    service.bind("claimed", "synthetic-playback")
    assert service.delete()["status"] == "deleted"
    assert not service.store.path("claimed").exists()
    assert not service.bind("claimed", "synthetic-playback")["model_ready"]


@pytest.mark.parametrize("bad", [
    [{"dwell_ms": 1, "down_down_ms": None, "flight_ms": None, "key": "secret"}],
    [{"dwell_ms": float("nan"), "down_down_ms": None, "flight_ms": None}],
    [{"dwell_ms": True, "down_down_ms": None, "flight_ms": None}],
    synthetic_window(1) + synthetic_window(1),
    None,
])
def test_invalid_data_clears_buffer_and_never_scores(service, bad):
    service.start("1", "enroll", consent=True)
    service.ingest(synthetic_window(1)[:1])
    result = service.ingest(bad)
    assert result["status"] == "invalid_samples"
    assert not service.active and not service.samples and result["verification"] is None


def test_insufficient_coverage_and_version_mismatch(service):
    enroll(service)
    service.start("holdout", "verify", consent=True)
    sparse = [{**s, "down_down_ms": None, "flight_ms": None} for s in synthetic_window(3)]
    assert service.ingest(sparse)["status"] == "insufficient_coverage"
    service.profile = replace(service.profile, feature_version="old")
    result = service.ingest(synthetic_window(3))
    assert result["verification"]["accepted"] is False
    assert result["verification"]["reason"] == "incompatible_feature_version"
    raw = json.loads(service.store.path("claimed").read_text())
    raw["profile"]["feature_version"] = "old"
    service.store.path("claimed").write_text(json.dumps(raw))
    assert service.bind("claimed", "synthetic-playback")["status"] == "profile_unavailable"
    assert service.profile is None


def test_demo_worker_enrollment_and_delete(tmp_path):
    worker = BehaviorWorker(tmp_path)
    assert worker.handle("play", {"action": "enroll-1", "consent": False})["status"] == "consent_required"
    for action in ("enroll-1", "enroll-2", "genuine", "impostor"):
        result = worker.handle("play", {"action": action, "consent": True})
    assert result["verification"]["reason"] == "behavior_mismatch"
    serialized = json.dumps(result)
    assert "synthetic-demo-user" not in serialized and "dwell_ms" not in serialized
    assert worker.handle("logout", None)["status"] == "stopped"
    assert worker.handle("delete", None)["status"] == "deleted"
    assert list(tmp_path.iterdir()) == []


def test_extreme_finite_inputs_cannot_emit_nonfinite_score(service):
    enroll(service)
    service.start("holdout", "verify", consent=True)
    samples = synthetic_window(3)
    for i, sample in enumerate(samples):
        sample["flight_ms"] = 1e308 if i % 2 else -1e308
    result = service.ingest(samples)
    assert result["status"] == "invalid_features"
    assert result["verification"] is None
    json.dumps(result, allow_nan=False)


def test_delete_selected_profile_preserves_other_user(service):
    enroll(service)
    other = MonitoringService(service.store, threshold=3)
    other.bind("other", "synthetic-playback")
    enroll(other)
    service.delete()
    assert other.store.path("other").exists()
    assert other.bind("other", "synthetic-playback")["model_ready"]


def test_delete_removes_interrupted_atomic_write_for_selected_user(service):
    enroll(service)
    path = service.store.path("claimed")
    leftover = path.parent / f".{path.stem}.interrupted.tmp"
    leftover.write_text("derived profile")
    service.delete()
    assert not leftover.exists() and not path.exists()
