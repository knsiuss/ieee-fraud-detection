"""Adaptive decision layer — LinUCB contextual bandit over the action space.

This is policy **v2**: it coexists with the static-threshold policy
(:mod:`fraud_detect.policy`, v1) and improves from human review feedback
over time, while staying auditable. Prediction and decisioning remain
separate — the model still emits a fraud probability, and this policy maps
it to APPROVE / MANUAL_REVIEW / DECLINE.

Why a contextual bandit instead of full sequential RL
-----------------------------------------------------
Transaction decisions are single-step: context in → action out → reward.
There is no validated sequential dependency between transactions that would
justify a value function over time. LinUCB (Chu et al., 2011) models each
arm's expected reward as a linear function of the context, which fits the
small discrete action space here and keeps the promotion math tractable.

Reward source
-------------
The existing ``reviewer outcome`` column in ``decisions.db`` (safe / fraud).
A reviewer verdict is the only trusted label signal available in the demo
(no live ground truth — see ``docs/MODEL_CARD.md``). Rewards are asymmetric
on purpose: blocking a legitimate customer and letting fraud slip through
do not cost the same. See :func:`reward_for`.

Selection bias
--------------
Auto-actioned transactions (score ≥ ``auto_action_above``) are never
reviewed, so their true label is unknown — a classic missing-at-random trap.
Mitigation: a configurable random **audit sampling** rate
(:attr:`BanditPolicy.audit_sample_rate`) routes a small random subset of
auto-actioned declines to the review queue, providing an unbiased estimate
of the false-positive rate among auto-declines. Rewards for non-sampled
auto-declines are never imputed.

Promotion (mirrors the retrain gate)
------------------------------------
A candidate policy version is evaluated **off-policy** on the logged
decision history via inverse propensity scoring (IPS), and promoted only if
its expected reward is ≥ the current policy's — the same
``new_auc >= old_auc`` anti-regression pattern used by ``api.store``.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .policy import Decision

#: Policy version id recorded on every bandit decision and event.
BANDIT_VERSION: str = "v2-linucb"

#: Discrete action space (same vocabulary as policy v1).
ACTIONS: tuple[str, ...] = (
    Decision.APPROVE.value,
    Decision.MANUAL_REVIEW.value,
    Decision.DECLINE.value,
)
ACTION_INDEX: dict[str, int] = {a: i for i, a in enumerate(ACTIONS)}
N_ACTIONS: int = len(ACTIONS)

#: Context vector dimension — see :func:`build_context`.
CONTEXT_DIM: int = 7

#: Default high-confidence cutoff: score ≥ this ⇒ auto-action (DECLINE)
#: without routing to the review queue. Deliberately a parameter, not a
#: constant: the model is only roughly calibrated (Brier 0.021, top decile
#: under-predicts — see docs/MODEL_CARD.md), so this cutoff will likely need
#: tuning after deployment via ``FRAUD_AUTO_ACTION_ABOVE``.
DEFAULT_AUTO_ACTION_ABOVE: float = 0.95

#: Default fraction of auto-actioned declines routed to review as a random
#: audit sample (selection-bias mitigation, see module docstring).
DEFAULT_AUDIT_SAMPLE_RATE: float = 0.05

#: Default LinUCB exploration bonus α.
DEFAULT_ALPHA: float = 1.0

#: Default random-exploration probability ε (epsilon-greedy on top of UCB,
#: used so off-policy evaluation has logged propensities that never hit 0).
DEFAULT_EPSILON: float = 0.10

# Business-justified reward table. Asymmetry is deliberate:
#   * DECLINE confirmed fraud         +1.0  correct block
#   * DECLINE overturned (FP)         -2.5  blocked a legitimate customer
#   * APPROVE correct (safe)          +0.5  low cost, mostly routine
#   * APPROVE wrong (fraud slipped)   -3.0  largest penalty (chargeback/fraud loss)
#   * MANUAL_REVIEW → fraud           +0.8  caught by human; correct flag
#   * MANUAL_REVIEW → safe            +0.1  review friction, but correct
REWARD_TABLE: dict[tuple[str, str], float] = {
    (Decision.DECLINE.value, "fraud"): 1.0,
    (Decision.DECLINE.value, "safe"): -2.5,
    (Decision.APPROVE.value, "safe"): 0.5,
    (Decision.APPROVE.value, "fraud"): -3.0,
    (Decision.MANUAL_REVIEW.value, "fraud"): 0.8,
    (Decision.MANUAL_REVIEW.value, "safe"): 0.1,
}

#: Exploration bonus is capped at the largest single-decision reward a
#: learned arm can achieve (max of REWARD_TABLE = 1.0). Without the cap,
#: an empty arm's UCB bonus α·√(x·x) can exceed 1.0 on high-signal
#: contexts (x·x > 1), which would let it outrank arms that are genuinely
#: learned — the policy would never converge toward rewarding actions.
UCB_BONUS_CAP: float = float(max(REWARD_TABLE.values()))


def reward_for(action: str, reviewer_outcome: str) -> float | None:
    """Reward for an (action, reviewer outcome) pair, or ``None`` if unknown.

    Unknown outcomes (e.g. ``None``, or a mismatch between action and
    outcome) return ``None`` so callers never write a fabricated reward.
    """
    if reviewer_outcome not in ("safe", "fraud"):
        return None
    return REWARD_TABLE.get((action, reviewer_outcome))


def build_context(
    probability: float,
    drivers: list[dict[str, Any]],
    input_features: dict[str, float],
) -> list[float]:
    """Build the fixed-dimension context vector for one transaction.

    The context reuses signals the platform already computes — no new
    feature work: the model score, the transaction amount, and the top-4
    SHAP contributions (sorted by |contribution|, padded with zeros). A
    trailing constant term serves as the intercept.

    Returns a list of length :data:`CONTEXT_DIM`.
    """
    raw_amount = input_features.get("TransactionAmt")
    amount_log = 0.0
    if raw_amount is not None:
        try:
            amount_log = math.log1p(max(float(raw_amount), 0.0)) / math.log1p(1000.0)
        except (TypeError, ValueError):
            amount_log = 0.0

    contributions = sorted(
        (float(d.get("contribution") or 0.0) for d in drivers),
        key=abs,
        reverse=True,
    )[:4]
    padded = contributions + [0.0] * (4 - len(contributions))

    return [float(probability), amount_log, *padded, 1.0]


@dataclass
class BanditArm:
    """One arm's LinUCB statistics: A (d×d) and b (d)."""

    n: int = 0
    a: list[list[float]] | None = None  # lazily sized to the context dim
    b: list[float] | None = None

    def _matrices(self, dim: int) -> tuple[np.ndarray, np.ndarray]:
        if self.a is None:
            self.a = np.eye(dim, dtype=float).tolist()
            self.b = [0.0] * dim
        return np.asarray(self.a, dtype=float), np.asarray(self.b, dtype=float)

    def update(self, context: list[float], reward: float) -> None:
        """Bayesian-ish incremental update with ``(x, r)``: A += x xᵀ, b += r x."""
        x = np.asarray(context, dtype=float)
        a, b = self._matrices(x.shape[0])
        a += np.outer(x, x)
        b += reward * x
        self.a = a.tolist()
        self.b = b.tolist()
        self.n += 1

    def update_reward(self, context: list[float], delta: float) -> None:
        """Correct ``b`` by ``delta·x`` when a verdict on an already-learned
        observation changes. The observation (context) is unchanged — only
        its reward is corrected — so ``A`` and ``n`` must not grow again.
        """
        x = np.asarray(context, dtype=float)
        _, b = self._matrices(x.shape[0])
        b += delta * x
        self.b = b.tolist()

    def theta(self, dim: int) -> np.ndarray:
        """Ridge-regularised weight estimate: solve(A + λI, b)."""
        a, b = self._matrices(dim)
        reg = np.eye(dim, dtype=float) * 1e-6
        try:
            return np.linalg.solve(a + reg, b)
        except np.linalg.LinAlgError:  # pragma: no cover - degenerate edge
            return np.linalg.pinv(a + reg) @ b

    def ucb_score(self, context: list[float], alpha: float) -> float:
        """Upper confidence bound θᵀx + α·√(xᵀA⁻¹x), bonus capped at UCB_BONUS_CAP.

        The cap keeps the exploration term comparable to the reward scale;
        see UCB_BONUS_CAP for why an uncapped bonus would stall learning.
        """
        x = np.asarray(context, dtype=float)
        a, _ = self._matrices(x.shape[0])
        theta = self.theta(x.shape[0])
        try:
            inv_a = np.linalg.inv(a)
        except np.linalg.LinAlgError:  # pragma: no cover - degenerate edge
            inv_a = np.linalg.pinv(a)
        bonus = float(np.sqrt(max(x @ inv_a @ x, 0.0)))
        return float(theta @ x) + alpha * min(bonus, UCB_BONUS_CAP)

    def as_dict(self) -> dict[str, Any]:
        return {"n": self.n, "a": self.a, "b": self.b}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BanditArm:
        return cls(n=int(data.get("n", 0)), a=data.get("a"), b=data.get("b"))


@dataclass
class BanditState:
    """Serialisable snapshot of a policy version's learned parameters."""

    version: str = BANDIT_VERSION
    arms: dict[str, BanditArm] = field(default_factory=dict)
    n_decisions: int = 0
    n_rewards: int = 0

    def arm(self, action: str) -> BanditArm:
        return self.arms.setdefault(action, BanditArm())

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "n_decisions": self.n_decisions,
            "n_rewards": self.n_rewards,
            "arms": {a: arm.as_dict() for a, arm in self.arms.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BanditState:
        return cls(
            version=str(data.get("version", BANDIT_VERSION)),
            arms={a: BanditArm.from_dict(v) for a, v in data.get("arms", {}).items()},
            n_decisions=int(data.get("n_decisions", 0)),
            n_rewards=int(data.get("n_rewards", 0)),
        )


@dataclass(frozen=True)
class BanditChoice:
    """One bandit decision plus everything needed for audit + IPS."""

    decision: Decision
    action: str
    needs_review: bool
    auto_actioned: bool
    audit_sampled: bool
    explored: bool
    propensity: float
    action_probs: dict[str, float]
    reason_code: str


@dataclass
class BanditPolicy:
    """Versioned contextual-bandit decision policy (v2).

    Parameters
    ----------
    version:
        Policy version id, recorded on every decision and event.
    alpha:
        LinUCB exploration bonus (higher ⇒ more exploration via UCB).
    epsilon:
        Probability of uniform random exploration (epsilon-greedy). Kept
        non-zero so every action has a strictly positive logged propensity,
        which is what makes off-policy evaluation possible.
    auto_action_above:
        Score at or above which the transaction is auto-actioned (DECLINE)
        without routing to the review queue. Configurable on purpose — the
        model is only roughly calibrated, so this needs tuning post-deploy.
    audit_sample_rate:
        Random audit-sampling fraction of auto-actioned declines, routed to
        review so the selection bias of auto-actioning can be measured.
    rng:
        Seeded random source (deterministic tests, configurable production).
    """

    version: str = BANDIT_VERSION
    alpha: float = DEFAULT_ALPHA
    epsilon: float = DEFAULT_EPSILON
    auto_action_above: float = DEFAULT_AUTO_ACTION_ABOVE
    audit_sample_rate: float = DEFAULT_AUDIT_SAMPLE_RATE
    rng: random.Random = field(default_factory=random.Random)

    def as_dict(self) -> dict[str, Any]:
        """Auditable snapshot of this policy version's parameters."""
        return {
            "policy_version": self.version,
            "alpha": self.alpha,
            "epsilon": self.epsilon,
            "auto_action_above": self.auto_action_above,
            "audit_sample_rate": self.audit_sample_rate,
        }

    def _exploration_probs(self, chosen: str, explored: bool) -> dict[str, float]:
        if explored:
            p = 1.0 / N_ACTIONS
            return {a: p for a in ACTIONS}
        p_other = self.epsilon / N_ACTIONS
        return {a: (1.0 - self.epsilon + p_other if a == chosen else p_other) for a in ACTIONS}

    def decide(
        self,
        probability: float,
        context: list[float],
        state: BanditState,
    ) -> BanditChoice:
        """Pick an action for one transaction, with full audit metadata."""
        if probability >= self.auto_action_above:
            sampled = self.rng.random() < self.audit_sample_rate
            probs = {Decision.DECLINE.value: 1.0}
            for a in ACTIONS:
                probs.setdefault(a, 0.0)
            return BanditChoice(
                decision=Decision.DECLINE,
                action=(
                    "Auto-decline: probability above the high-confidence cutoff "
                    "(no manual review)."
                ),
                needs_review=sampled,
                auto_actioned=True,
                audit_sampled=sampled,
                explored=False,
                propensity=1.0,
                action_probs=probs,
                reason_code=(
                    f"bandit:auto-decline (score {probability:.3f} >= "
                    f"auto_action_above {self.auto_action_above})"
                ),
            )

        explored = self.rng.random() < self.epsilon
        if explored:
            chosen = self.rng.choice(ACTIONS)
        else:
            scores = {
                a: state.arm(a).ucb_score(context, self.alpha) for a in ACTIONS
            }
            chosen = max(scores, key=scores.get)

        probs = self._exploration_probs(chosen, explored)
        decision = Decision(chosen)
        return BanditChoice(
            decision=decision,
            action=self._action_text(decision),
            needs_review=decision == Decision.MANUAL_REVIEW,
            auto_actioned=False,
            audit_sampled=False,
            explored=explored,
            propensity=probs[chosen],
            action_probs=probs,
            reason_code=(
                f"bandit:v2 ({'explored' if explored else 'greedy'}, "
                f"propensity {probs[chosen]:.3f})"
            ),
        )

    @staticmethod
    def _action_text(decision: Decision) -> str:
        if decision == Decision.APPROVE:
            return "Approve. Adaptive policy: risk below review threshold."
        if decision == Decision.MANUAL_REVIEW:
            return "Manual review. Adaptive policy: request additional verification."
        return "Decline. Adaptive policy: probability exceeds decline threshold."

    def update_arms(
        self,
        state: BanditState,
        context: list[float],
        action: str,
        reward: float,
    ) -> None:
        """Fold one (context, action, reward) into the state's statistics."""
        state.arm(action).update(context, reward)
        state.n_rewards += 1


# Persistence


def save_state(state: BanditState, path: Path | str) -> Path:
    """Atomically persist a bandit state to ``path`` (write-then-replace)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state.as_dict(), indent=2), encoding="utf-8")
    tmp.replace(out)
    return out


def load_state(path: Path | str) -> BanditState | None:
    """Load a bandit state, or ``None`` if ``path`` does not exist / is corrupt."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return BanditState.from_dict(data)


# Off-policy evaluation & promotion (mirrors the retrain gate)


def fit_offline(events: list[dict[str, Any]], version: str = "v2-candidate") -> BanditState:
    """Fit a candidate policy state from logged (context, action, reward) events.

    The candidate is trained on exactly the information a deployed policy
    would have: the logged contexts and the rewards the *logging* policy
    actually collected. It is then evaluated against the live policy on the
    same log — never on fresh data, so the comparison is honest.
    """
    state = BanditState(version=version)
    for action in ACTIONS:
        state.arm(action)
    for event in events:
        context = event.get("context")
        action = event.get("action")
        reward = event.get("reward")
        if not context or action not in ACTION_INDEX or reward is None:
            continue
        state.arm(action).update(list(context), float(reward))
        state.n_decisions += 1
        # The candidate becomes the live checkpoint on promotion, and the
        # cold-start gate (``_BANDIT_MIN_REWARDS``) reads ``n_rewards`` — it
        # must reflect the rewarded history the candidate was trained on, or
        # the first promotion would knock the bandit back into cold start.
        state.n_rewards += 1
    return state


def evaluate_off_policy(events: list[dict[str, Any]], state: BanditState) -> dict[str, float | int]:
    """Inverse-propensity estimate of ``state``'s expected reward on a log.

    For each logged event, the candidate policy's greedy action is computed.
    If it coincides with the action that was actually logged, the observed
    reward is re-weighted by the inverse of the logged propensity
    (self-normalised IPS): ``V̂ = Σ r·I(π(x)=a)/p / Σ I(π(x)=a)/p``.

    Caveat: the estimate is only unbiased under the logged exploration
    policy — which is why epsilon-greedy keeps propensities strictly
    positive. With few overlapping actions the estimate has high variance;
    promotion therefore requires enough overlap (``n_overlap`` is reported).
    """
    total_weight = 0.0
    weighted_reward = 0.0
    n_overlap = 0
    for event in events:
        context = event.get("context")
        action = event.get("action")
        propensity = event.get("propensity")
        reward = event.get("reward")
        if not context or action not in ACTION_INDEX or propensity is None:
            continue
        if reward is None:
            continue
        scores = {
            a: state.arm(a).ucb_score(list(context), DEFAULT_ALPHA) for a in ACTIONS
        }
        if max(scores, key=scores.get) != action:
            continue
        weight = 1.0 / max(float(propensity), 1e-6)
        weighted_reward += float(reward) * weight
        total_weight += weight
        n_overlap += 1

    ips = float(weighted_reward / max(total_weight, 1e-9)) if n_overlap else 0.0
    return {"ips": ips, "n_overlap": n_overlap, "n_logged": len(events)}


def maybe_promote_bandit(
    candidate: BanditState,
    current: BanditState,
    events: list[dict[str, Any]],
    min_improvement: float = 0.0,
) -> dict[str, Any]:
    """Anti-regression gate for policy versions: promote only if candidate ≥ current.

    Returns a report dict with ``promoted``, ``candidate_ips``, ``current_ips``
    and ``n_overlap`` — mirroring the model retrain gate
    (``api.store.retrain_and_swap``): a losing candidate never touches the
    live policy.
    """
    candidate_eval = evaluate_off_policy(events, candidate)
    current_eval = evaluate_off_policy(events, current)
    promoted = bool(
        candidate_eval["n_overlap"] > 0
        and candidate_eval["ips"] >= current_eval["ips"] + min_improvement
    )
    return {
        "promoted": promoted,
        "candidate_ips": candidate_eval["ips"],
        "current_ips": current_eval["ips"],
        "n_overlap": candidate_eval["n_overlap"],
        "n_logged": candidate_eval["n_logged"],
        "reason": (
            "Candidate beats the live policy on off-policy (IPS) evaluation; promoted."
            if promoted
            else (
                "Candidate did not beat the live policy on off-policy (IPS) "
                "evaluation; kept current."
            )
        ),
    }
