"""Build a user profile from complete enrollment windows."""

from packages.behavioral_ai.features import extract_window, feature_vector
from packages.behavioral_ai.models.profile import UserProfile


def enroll_user(user_id, windows):
    """Enroll one user from at least two valid timing windows.

    Each window must contain exactly 100 samples and belong to this user.
    Callers must preserve recording session boundaries when forming windows.
    Invalid or low-coverage windows cause enrollment to fail.
    """
    vectors = []

    for index, samples in enumerate(windows):
        features = extract_window(samples)

        if features is None:
            raise ValueError(
                f"Enrollment window {index} has insufficient "
                "transition coverage."
            )

        vectors.append(feature_vector(features))

    return UserProfile.fit(user_id, vectors)