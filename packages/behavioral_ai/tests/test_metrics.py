import pytest

from packages.behavioral_ai.evaluation.metrics import summarize_trials
from packages.behavioral_ai.evaluation.scoring import VerificationTrial


def make_trial(distance, kind="genuine"):
    sources = {
        "genuine": ("alice", True),
        "enrolled_impostor": ("bob", True),
        "unknown": ("charlie", False),
    }
    source_user_id, source_enrolled = sources[kind]

    return VerificationTrial(
        claimed_user_id="alice",
        source_user_id=source_user_id,
        session_id=f"{kind}-session",
        window_index=0,
        distance=distance,
        source_enrolled=source_enrolled,
    )


def test_counts_errors_and_calculates_rates():
    trials = [
        make_trial(1.0),
        make_trial(3.0),
        make_trial(1.0, "enrolled_impostor"),
        make_trial(4.0, "enrolled_impostor"),
        make_trial(1.5, "unknown"),
        make_trial(5.0, "unknown"),
    ]

    metrics = summarize_trials(trials, threshold=2.0)

    assert metrics.threshold == 2.0
    assert metrics.genuine_trials == 2
    assert metrics.false_rejections == 1
    assert metrics.false_rejection_rate == pytest.approx(0.5)

    assert metrics.impostor_trials == 4
    assert metrics.false_acceptances == 2
    assert metrics.false_acceptance_rate == pytest.approx(0.5)

    assert metrics.unknown_trials == 2
    assert metrics.unknown_false_acceptances == 1
    assert metrics.unknown_false_acceptance_rate == pytest.approx(0.5)


def test_accepts_distance_equal_to_threshold():
    trials = [
        make_trial(2.0),
        make_trial(2.0, "unknown"),
    ]

    metrics = summarize_trials(trials, threshold=2.0)

    assert metrics.false_rejections == 0
    assert metrics.false_acceptances == 1
    assert metrics.unknown_false_acceptances == 1


def test_genuine_only_leaves_impostor_rates_undefined():
    metrics = summarize_trials(
        [make_trial(1.0), make_trial(3.0)],
        threshold=2.0,
    )

    assert metrics.false_rejection_rate == pytest.approx(0.5)
    assert metrics.false_acceptance_rate is None
    assert metrics.unknown_false_acceptance_rate is None


def test_unknown_only_leaves_genuine_rate_undefined():
    metrics = summarize_trials(
        [make_trial(1.0, "unknown"), make_trial(3.0, "unknown")],
        threshold=2.0,
    )

    assert metrics.false_rejection_rate is None
    assert metrics.false_acceptance_rate == pytest.approx(0.5)
    assert metrics.unknown_false_acceptance_rate == pytest.approx(0.5)


def test_enrolled_impostors_are_not_counted_as_unknown():
    metrics = summarize_trials(
        [make_trial(1.0, "enrolled_impostor")],
        threshold=2.0,
    )

    assert metrics.impostor_trials == 1
    assert metrics.false_acceptances == 1
    assert metrics.unknown_trials == 0
    assert metrics.unknown_false_acceptance_rate is None


def test_supports_single_pass_trial_iterator():
    trials = [
        make_trial(1.0),
        make_trial(4.0, "unknown"),
    ]

    assert summarize_trials(iter(trials), threshold=2.0) == summarize_trials(
        trials, threshold=2.0
    )


def test_rejects_empty_trials():
    with pytest.raises(ValueError, match="At least one verification trial"):
        summarize_trials([], threshold=2.0)


@pytest.mark.parametrize(
    "threshold",
    [-1, True, None, "2", float("nan"), float("inf")],
)
def test_rejects_invalid_threshold(threshold):
    with pytest.raises(ValueError, match="Threshold"):
        summarize_trials([make_trial(1.0)], threshold=threshold)


@pytest.mark.parametrize(
    "distance",
    [-1, True, None, "2", float("nan"), float("inf")],
)
def test_rejects_invalid_trial_distance(distance):
    with pytest.raises(ValueError, match="Trial distances"):
        summarize_trials([make_trial(distance)], threshold=2.0)


def test_rejects_genuine_trial_marked_as_unenrolled():
    trial = VerificationTrial(
        claimed_user_id="alice",
        source_user_id="alice",
        session_id="invalid",
        window_index=0,
        distance=1.0,
        source_enrolled=False,
    )

    with pytest.raises(ValueError, match="genuine trial"):
        summarize_trials([trial], threshold=2.0)