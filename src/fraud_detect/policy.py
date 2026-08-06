"""Decision policy — turns a fraud probability into a business decision.

Prediction (``serving.predict_proba``) and decisioning are deliberately
separate: the model outputs a probability, and a **versioned policy** maps it
to APPROVE / MANUAL_REVIEW / DECLINE. Thresholds and actions can change
without retraining the model, and every decision records the policy version
and thresholds that were applied so the audit trail stays truthful.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Decision(str, Enum):
    """Business decisions a policy can emit."""

    APPROVE = "APPROVE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    DECLINE = "DECLINE"


@dataclass(frozen=True)
class DecisionPolicy:
    """A versioned threshold policy.

    Parameters
    ----------
    version:
        Policy version id, recorded on every decision.
    review_above:
        Probability at or above which the transaction enters MANUAL_REVIEW.
    decline_above:
        Probability at or above which the transaction is DECLINED.
    """

    version: str
    review_above: float
    decline_above: float
    #: Human-readable action text per decision.
    actions: dict[str, str] = field(
        default_factory=lambda: {
            Decision.APPROVE.value: "Approve. Probability below the review threshold.",
            Decision.MANUAL_REVIEW.value: "Manual review. Request additional verification.",
            Decision.DECLINE.value: "Decline. Probability exceeds the decline threshold.",
        }
    )

    def apply(self, probability: float) -> tuple[Decision, str]:
        """Map a fraud probability to a (decision, action) pair."""
        if probability >= self.decline_above:
            decision = Decision.DECLINE
        elif probability >= self.review_above:
            decision = Decision.MANUAL_REVIEW
        else:
            decision = Decision.APPROVE
        return decision, self.actions[decision.value]

    def as_dict(self) -> dict[str, float | str]:
        return {
            "policy_version": self.version,
            "review_above": self.review_above,
            "decline_above": self.decline_above,
        }


#: Default policy for the demo. Thresholds align with the risk tiers used by
#: the web console. Overridable via ``DECISION_REVIEW_ABOVE`` /
#: ``DECISION_DECLINE_ABOVE`` environment variables at startup.
DEFAULT_POLICY = DecisionPolicy(
    version="v1",
    review_above=0.15,
    decline_above=0.50,
)


def policy_from_env(
    review_above: float | None = None,
    decline_above: float | None = None,
) -> DecisionPolicy:
    """Build a policy from explicit overrides, otherwise the defaults."""
    return DecisionPolicy(
        version=DEFAULT_POLICY.version,
        review_above=DEFAULT_POLICY.review_above if review_above is None else review_above,
        decline_above=DEFAULT_POLICY.decline_above if decline_above is None else decline_above,
    )
