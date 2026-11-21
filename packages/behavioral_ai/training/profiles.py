"""Fit user profiles using training sessions only."""

from packages.behavioral_ai.features import extract_windows, feature_vector
from packages.behavioral_ai.legacy.extract_features import validate_session
from packages.behavioral_ai.models.profile import UserProfile
from packages.behavioral_ai.training.splits import split_sessions


def train_profiles(sessions, split):
    """Return profiles indexed by enrolled user ID.

    Feature extraction runs separately for each training session.
    Incomplete tails and low-coverage windows are excluded by the shared
    extractor. Each user must have at least two usable training windows.
    """
    validated_split = split_sessions(
        sessions,
        train_ids=split.train_ids,
        development_ids=split.development_ids,
        test_ids=split.test_ids,
    )

    user_vectors = {}

    for session_id in validated_split.train_ids:
        session = sessions[session_id]
        validate_session(session)

        if session["session_id"] != session_id:
            raise ValueError(
                f"Session ID does not match its lookup key: {session_id}"
            )

        user_id = session["participant_id"]
        vectors = user_vectors.setdefault(user_id, [])

        for _, features in extract_windows(session["samples"]):
            vectors.append(feature_vector(features))

    profiles = {}

    for user_id in sorted(user_vectors):
        try:
            profiles[user_id] = UserProfile.fit(
                user_id,
                user_vectors[user_id],
            )
        except ValueError as error:
            raise ValueError(
                f"Could not train profile for {user_id}: {error}"
            ) from error

    return profiles
