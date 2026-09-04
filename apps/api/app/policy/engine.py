from typing import Optional

from app.domain.cases import (
    AIProposal,
    CaseStatus,
    PolicyDecision,
    ReconciliationCase,
    RiskLevel,
)
from app.domain.policy_config import PolicyConfig, PolicyThresholds, PolicyRuleToggles, default_policy_config


class PolicyEngine:
    def __init__(self, version: str = "1.0", config: Optional[PolicyConfig] = None):
        self.version = version
        # Live config. If none is provided, fall back to a default in-memory
        # config (used by unit tests / when Mongo is unavailable). Runtime
        # instances feed the stored config so edits apply immediately.
        self._config = config
        self._repo = None

    def _with_repo(self, repo=None) -> "PolicyEngine":
        """Attach a repository so evaluations reflect the persisted config."""
        if repo is None:
            from app.policy.repository import PolicyConfigRepository

            repo = PolicyConfigRepository()
        self._repo = repo
        return self

    async def _get_config(self) -> PolicyConfig:
        if self._config is not None:
            return self._config
        if self._repo is not None:
            return await self._repo.get()
        return default_policy_config()

    def _set_config(self, config: PolicyConfig):
        self._config = config
        return self

    @property
    def thresholds(self) -> PolicyThresholds:
        cfg = self._config or default_policy_config()
        return cfg.thresholds

    @property
    def toggles(self) -> PolicyRuleToggles:
        cfg = self._config or default_policy_config()
        return cfg.toggles

    async def evaluate(
        self,
        case: ReconciliationCase,
        proposal: Optional[AIProposal] = None,
        user_role: Optional[str] = None,
    ) -> PolicyDecision:
        cfg = await self._get_config()
        th = cfg.thresholds
        tg = cfg.toggles
        reason_codes: list[str] = []
        required_role: Optional[str] = None
        evidence_requirements: list[str] = []
        allowed = False
        decision = "DENY"

        # 1. Amount impact gate
        if tg.enforce_high_impact_gate and abs(case.amount) > th.high_impact_threshold:
            decision = "HUMAN_REVIEW"
            reason_codes.append("high_monetary_impact")
            required_role = "REVIEWER"
            evidence_requirements.append("reviewer_approval_required")
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        # 2. Risk gate
        risk_allowed = self._risk_allowed(case.risk, tg)
        if not risk_allowed:
            decision = "HUMAN_REVIEW"
            reason_codes.append(f"risk_level_{case.risk.value}")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        # 3. If auto-resolve path (deterministic only)
        if proposal is None:
            if tg.require_low_risk_for_deterministic_auto_close and case.risk != RiskLevel.LOW:
                decision = "HUMAN_REVIEW"
                reason_codes.append("risk_not_low")
                required_role = "REVIEWER"
                return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)
            if case.match_score < th.auto_close_match_score:
                decision = "HUMAN_REVIEW"
                reason_codes.append("match_score_below_threshold")
                required_role = "REVIEWER"
                return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)
            allowed = True
            decision = "AUTO_CLOSE"
            reason_codes.append("deterministic_auto_close_eligible")
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        # 4. AI proposal path
        if proposal.conclusion == "INSUFFICIENT_EVIDENCE":
            decision = "KEEP_EXCEPTION"
            reason_codes.append("insufficient_evidence")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        if proposal.confidence < th.confidence_threshold:
            decision = "HUMAN_REVIEW"
            reason_codes.append("low_confidence")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        if not self._proposed_risk_allowed(proposal.risk_level, tg):
            decision = "HUMAN_REVIEW"
            reason_codes.append(f"proposed_risk_{proposal.risk_level.value}")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        if not proposal.evidence_ids or len(proposal.evidence_ids) < th.min_evidence_ids:
            decision = "HUMAN_REVIEW"
            reason_codes.append("insufficient_evidence_ids")
            evidence_requirements.append(f"at_least_{th.min_evidence_ids}_evidence_ids")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        if proposal.proposed_action not in ("AUTO_CLOSE", "MATCH", "RESOLVE"):
            decision = "HUMAN_REVIEW"
            reason_codes.append("proposed_action_not_auto_close")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        if tg.enforce_multi_candidate_gate and case.deterministic_info and len(case.deterministic_info.candidate_ids) > 1:
            decision = "HUMAN_REVIEW"
            reason_codes.append("multiple_candidates")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        diff = abs(case.discrepancy.amount_diff) if case.discrepancy else 0
        if tg.enforce_discrepancy_tolerance and diff > th.max_auto_tolerance:
            decision = "HUMAN_REVIEW"
            reason_codes.append("discrepancy_above_tolerance")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        allowed = True
        decision = "AUTO_CLOSE"
        reason_codes.append("ai_proposal_passes_policy")
        return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

    def _risk_allowed(self, risk: RiskLevel, tg: PolicyRuleToggles) -> bool:
        if risk == RiskLevel.LOW:
            return True
        if risk == RiskLevel.MEDIUM:
            return tg.auto_close_medium_risk
        # HIGH / CRITICAL
        return tg.auto_close_high_risk

    def _proposed_risk_allowed(self, risk: RiskLevel, tg: PolicyRuleToggles) -> bool:
        if risk == RiskLevel.LOW:
            return True
        if risk == RiskLevel.MEDIUM:
            return tg.auto_close_medium_risk
        return tg.auto_close_high_risk

    def evaluate_human_action(
        self,
        case: ReconciliationCase,
        action: str,
        user_role: str,
    ) -> PolicyDecision:
        allowed_roles = {
            "ADMIN": {"approve", "reject", "keep-exception", "investigate"},
            "FINANCE_CONTROLLER": {"approve", "reject", "keep-exception", "investigate"},
            "REVIEWER": {"approve", "reject", "keep-exception"},
            "VIEWER": set(),
        }
        if user_role not in allowed_roles:
            return self._decision(False, "DENY", ["insufficient_role"], "ADMIN")
        if action in allowed_roles[user_role]:
            return self._decision(True, "ALLOW", ["role_authorized"], user_role)
        return self._decision(False, "DENY", ["action_not_allowed_for_role"], user_role)

    def _decision(self, allowed, decision, reason_codes, required_role, evidence_requirements=None) -> PolicyDecision:
        return PolicyDecision(
            allowed=allowed,
            decision=decision,
            reason_codes=reason_codes,
            required_role=required_role,
            evidence_requirements=evidence_requirements or [],
            policy_version=self.version,
        )