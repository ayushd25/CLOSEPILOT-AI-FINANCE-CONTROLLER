from typing import Optional

from app.domain.cases import (
    AIProposal,
    CaseStatus,
    PolicyDecision,
    ReconciliationCase,
    RiskLevel,
)

REQUIRED_EVIDENCE_COMPLETENESS = 0.6
LOW_RISK_THRESHOLD = RiskLevel.LOW
CONFIDENCE_THRESHOLD = 0.7
MAX_AUTO_TOLERANCE = 200  # minor units

HIGH_IMPACT_THRESHOLD = 50_00_000  # ₹50,000.00


class PolicyEngine:
    def __init__(self, version: str = "1.0"):
        self.version = version

    def evaluate(
        self,
        case: ReconciliationCase,
        proposal: Optional[AIProposal] = None,
        user_role: Optional[str] = None,
    ) -> PolicyDecision:
        reason_codes: list[str] = []
        required_role: Optional[str] = None
        evidence_requirements: list[str] = []
        allowed = False
        decision = "DENY"

        # 1. Amount impact gate
        if abs(case.amount) > HIGH_IMPACT_THRESHOLD:
            decision = "HUMAN_REVIEW"
            reason_codes.append("high_monetary_impact")
            required_role = "REVIEWER"
            evidence_requirements.append("reviewer_approval_required")
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        # 2. Risk gate
        if case.risk in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL):
            decision = "HUMAN_REVIEW"
            reason_codes.append(f"risk_level_{case.risk.value}")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        # 3. If auto-resolve path (deterministic only)
        if proposal is None:
            if case.risk != RiskLevel.LOW:
                decision = "HUMAN_REVIEW"
                reason_codes.append("risk_not_low")
                required_role = "REVIEWER"
                return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)
            if case.match_score < 100:
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

        if proposal.confidence < CONFIDENCE_THRESHOLD:
            decision = "HUMAN_REVIEW"
            reason_codes.append("low_confidence")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        if proposal.risk_level != RiskLevel.LOW:
            decision = "HUMAN_REVIEW"
            reason_codes.append(f"proposed_risk_{proposal.risk_level.value}")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        if not proposal.evidence_ids or len(proposal.evidence_ids) < 2:
            decision = "HUMAN_REVIEW"
            reason_codes.append("insufficient_evidence_ids")
            evidence_requirements.append("at_least_2_evidence_ids")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        if proposal.proposed_action not in ("AUTO_CLOSE", "MATCH", "RESOLVE"):
            decision = "HUMAN_REVIEW"
            reason_codes.append("proposed_action_not_auto_close")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        if case.deterministic_info and len(case.deterministic_info.candidate_ids) > 1:
            decision = "HUMAN_REVIEW"
            reason_codes.append("multiple_candidates")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        if abs(case.discrepancy.amount_diff) if case.discrepancy else 0 > MAX_AUTO_TOLERANCE:
            decision = "HUMAN_REVIEW"
            reason_codes.append("discrepancy_above_tolerance")
            required_role = "REVIEWER"
            return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

        allowed = True
        decision = "AUTO_CLOSE"
        reason_codes.append("ai_proposal_passes_policy")
        return self._decision(allowed, decision, reason_codes, required_role, evidence_requirements)

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
