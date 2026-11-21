import pytest

from packages.behavioral_ai.evaluation.calibration import calibrate_threshold
from packages.behavioral_ai.evaluation.scoring import VerificationTrial


def make_trial(distance, genuine=True):
    return VerificationTrial(
        claimed_user_id="alice",
        source_user_id="alice" if genuine else "charlie",
        session_id="genuine-session" if genuine else "unknown-session",
        window_index=0,
        distance=distance,
        source_enrolled=genuine,
    )


def make_trials(genuine_distances, impostor_distances):
    return [
        *[make_trial(distance) for distance in genuine_distances],
        *[
            make_trial(distance, genuine=False)
            for distance in impostor_distances
        ],
    ]


def test_selects_threshold_that_separates_development_trials():
    trials = make_trials([1.0, 2.0], [4.0, 5.0])

    result = calibrate_threshold(trials)

    assert result.threshold == 2.0
    assert result.balanced_error_rate == 0.0
    assert result.development_metrics.false_rejections == 0
    assert result.development_metrics.false_acceptances == 0
    assert result.development_metrics.threshold == result.threshold


def test_selects_lower_threshold_when_error_rates_tie():
    trials = make_trials([1.0, 3.0], [2.0, 4.0])

    result = calibrate_threshold(trials)

    # Thresholds 1 and 3 both produce a balanced error rate of 0.25.
    assert result.threshold == 1.0
    assert result.balanced_error_rate == pytest.approx(0.25)


def test_balances_rates_instead_of_minimizing_total_error_count():
    trials = make_trials(
        [1.0, 2.0],
        [1.5] * 8 + [3.0] * 2,
    )

    result = calibrate_threshold(trials)

    assert result.threshold == 1.0
    assert result.development_metrics.false_rejection_rate == 0.5
    assert result.development_metrics.false_acceptance_rate == 0.0
    assert result.balanced_error_rate == 0.25


def test_can_choose_zero_to_reject_all_positive_distances():
    trials = make_trials([2.0], [1.0])

    result = calibrate_threshold(trials)

    assert result.threshold == 0.0
    assert result.development_metrics.false_rejections == 1
    assert result.development_metrics.false_acceptances == 0


def test_zero_distance_is_accepted_at_zero_threshold():
    trials = make_trials([0.0], [0.0])

    result = calibrate_threshold(trials)

    assert result.threshold == 0.0
    assert result.development_metrics.false_rejections == 0
    assert result.development_metrics.false_acceptances == 1
    assert result.balanced_error_rate == 0.5


def test_handles_duplicate_distances():
    trials = make_trials([1.0, 1.0], [2.0, 2.0])

    result = calibrate_threshold(trials)

    assert result.threshold == 1.0
    assert result.balanced_error_rate == 0.0


def test_result_does_not_depend_on_trial_order():
    trials = make_trials([1.0, 3.0], [2.0, 4.0])

    assert calibrate_threshold(trials) == calibrate_threshold(
        list(reversed(trials))
    )


def test_supports_single_pass_iterator():
    trials = make_trials([1.0, 2.0], [4.0, 5.0])

    assert calibrate_threshold(iter(trials)) == calibrate_threshold(trials)


@pytest.mark.parametrize(
    "trials",
    [
        make_trials([1.0], []),
        make_trials([], [2.0]),
    ],
)
def test_requires_both_genuine_and_impostor_trials(trials):
    with pytest.raises(ValueError, match="both genuine and impostor"):
        calibrate_threshold(trials)


def test_rejects_empty_development_trials():
    with pytest.raises(ValueError, match="At least one verification trial"):
        calibrate_threshold([])


def test_rejects_invalid_distance():
    trials = make_trials([float("nan")], [2.0])

    with pytest.raises(ValueError, match="Trial distances"):
        calibrate_threshold(trials)