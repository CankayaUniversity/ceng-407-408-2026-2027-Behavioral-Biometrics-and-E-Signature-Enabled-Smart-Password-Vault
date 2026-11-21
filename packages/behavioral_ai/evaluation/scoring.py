"""Produce verification distances for evaluation sessions."""

import math
from dataclasses import dataclass

from packages.behavioral_ai.features import (
    FEATURE_VERSION,
    extract_windows,
    feature_vector,
)
from packages.behavioral_ai.legacy.extract_features import validate_session
from packages.behavioral_ai.training.splits import validate_ids


@dataclass(frozen=True)
class VerificationTrial:
    claimed_user_id: str
    source_user_id: str
    session_id: str
    window_index: int
    distance: float
    source_enrolled: bool

    @property
    def is_genuine(self):
        return self.claimed_user_id == self.source_user_id


def score_sessions(sessions, session_ids, profiles):
    """Compare each usable window against every enrolled profile.

    Each session is processed separately. A requested session without
    usable windows causes evaluation to fail.
    """
    if not profiles:
        raise ValueError("At least one enrolled profile is required.")

    ids = validate_ids(session_ids, "Evaluation")

    for user_id, profile in profiles.items():
        if profile.user_id != user_id:
            raise ValueError("Profile user ID does not match its lookup key.")

        if profile.feature_version != FEATURE_VERSION:
            raise ValueError("Incompatible profile feature version.")

    trials = []

    for session_id in ids:
        if session_id not in sessions:
            raise ValueError(f"Unknown evaluation session: {session_id}")

        session = sessions[session_id]
        validate_session(session)

        if session["session_id"] != session_id:
            raise ValueError(
                f"Session ID does not match its lookup key: {session_id}"
            )

        windows = list(extract_windows(session["samples"]))

        if not windows:
            raise ValueError(
                f"Evaluation session has no usable windows: {session_id}"
            )

        source_user_id = session["participant_id"]

        for window_index, features in windows:
            vector = feature_vector(features)

            for claimed_user_id in sorted(profiles):
                distance = profiles[claimed_user_id].distance(vector)

                if not math.isfinite(distance):
                    raise ValueError(
                        f"Non-finite distance in session: {session_id}"
                    )

                trials.append(
                    VerificationTrial(
                        claimed_user_id=claimed_user_id,
                        source_user_id=source_user_id,
                        session_id=session_id,
                        window_index=window_index,
                        distance=distance,
                        source_enrolled=source_user_id in profiles,
                    )
                )

    return tuple(trials)