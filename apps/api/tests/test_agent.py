"""Agent unit + integration tests.

Unit tests cover intent classification, plan parsing, and JSON recovery
without a database. Integration tests exercise the authorised executor
(policy-gated auto-close vs stage-for-review) against a real MongoDB and are
skipped when it is unavailable.
"""

import pytest

from app.agent.executor import AgentToolError
from app.agent.supervisor import AgentSupervisor, AgentIntent
from app.ai.parsing import extract_json_object
from app.domain.cases import ReconciliationCase, CaseStatus, RiskLevel


class _FakeLLMResponse:
    def __init__(self, content: str):
        self.content = content


def _fake_llm(text: str):
    class Fake:
        def invoke(self, _):
            return _FakeLLMResponse(text)

    return Fake()


# ------------------------------------------------------------------ #
# Pure unit tests (no DB). These are async because the agent methods   #
# are async; the module-level asyncio mark handles the event loop.    #
# ------------------------------------------------------------------ #
async def test_extract_json_object_parses_fenced():
    text = 'Here is the result:\n```json\n{"answer": "hello"}\n```\nDone.'
    assert extract_json_object(text) == {"answer": "hello"}


async def test_intent_classifies_question():
    supervisor = AgentSupervisor(session_id="test")
    supervisor._llm = _fake_llm('{"intent": "QUESTION"}')
    assert await supervisor._classify_intent("how many cases are open?") == AgentIntent.QUESTION


async def test_intent_classifies_task():
    supervisor = AgentSupervisor(session_id="test")
    supervisor._llm = _fake_llm('{"intent": "TASK"}')
    assert await supervisor._classify_intent("handle all mismatched transactions") == AgentIntent.TASK


async def test_plan_builds_steps():
    supervisor = AgentSupervisor(session_id="test")
    supervisor._llm = _fake_llm(
        '{"steps": [{"action": "close mismatches", "tool": "handle_mismatched_cases", "args": {}}]}'
    )
    plan = await supervisor._plan("handle all mismatched transactions")
    assert len(plan) == 1
    assert plan[0].tool == "handle_mismatched_cases"
    assert plan[0].step == 1


async def test_malformed_plan_raises():
    supervisor = AgentSupervisor(session_id="test")
    supervisor._llm = _fake_llm('{"steps": [{"tool": 5}]}')
    with pytest.raises(ValueError):
        await supervisor._plan("handle all mismatched transactions")


async def test_answer_question_returns_answer():
    class _FakeExec:
        async def summary(self, args=None):
            return {"total_cases": 10, "resolved": 6}

    supervisor = AgentSupervisor(session_id="test")
    supervisor._llm = _fake_llm('{"answer": "There are 6 resolved cases out of 10."}')
    supervisor.executor = _FakeExec()
    answer = await supervisor._answer_question("how many cases are resolved?")
    assert "6" in answer


async def test_answer_question_includes_case_detail_when_referenced():
    """A question referencing a CASE id must load that case's context for the LLM."""
    fetched = []

    class _FakeExec:
        async def summary(self, args=None):
            return {"total_cases": 5}

        async def get_case(self, args):
            fetched.append(args.get("case_id"))
            return {
                "case_id": "CASE_pay_1",
                "status": "HUMAN_REVIEW",
                "risk": "HIGH",
                "outcome_type": "amount_mismatch",
                "record_type": "payment",
                "amount": 500000,
                "currency": "INR",
                "match_score": 70.0,
                "related_record_ids": ["pay_1", "set_1"],
                "discrepancy": {"amount_diff": 335000, "currency": "INR", "detail": "amount_mismatch"},
                "deterministic_info": {"rules_triggered": ["amount_mismatch"], "reason_codes": ["high_amount"]},
                "ai_proposal": {"conclusion": "INSUFFICIENT_EVIDENCE", "confidence": 0.4, "risk_level": "HIGH"},
            }

    supervisor = AgentSupervisor(session_id="test")
    # Inspect the context the supervisor builds by stubbing the LLM to echo what it receives.
    captured = {}

    class _EchoLLM:
        def invoke(self, prompt):
            captured["prompt"] = prompt
            return _FakeLLMResponse('{"answer": "ok"}')

    supervisor._llm = _EchoLLM()
    supervisor.executor = _FakeExec()
    await supervisor._answer_question("What can you tell me about CASE_pay_1?")

    assert fetched == ["CASE_pay_1"], "Agent should load the referenced case"
    assert "CASE DETAIL CASE_pay_1" in captured["prompt"]
    assert "Risk level: HIGH" in captured["prompt"]
    assert "Amount: 500000 INR" in captured["prompt"]


async def test_unknown_tool_calls_field_missing():
    from app.agent.executor import TOOL_REGISTRY

    assert "handle_mismatched_cases" in TOOL_REGISTRY
    assert "summary" in TOOL_REGISTRY
    assert "investigate_cases" in TOOL_REGISTRY


# ------------------------------------------------------------------ #
# Integration tests (MongoDB required; skipped otherwise)            #
# ------------------------------------------------------------------ #
pytestmark = pytest.mark.asyncio

MONGODB_AVAILABLE = None


async def _mongodb_available() -> bool:
    try:
        from app.db import Database

        db = Database.get_db()
        await db.command("ping")
        return True
    except Exception:
        return False


async def _require_mongodb():
    global MONGODB_AVAILABLE
    if MONGODB_AVAILABLE is None:
        MONGODB_AVAILABLE = await _mongodb_available()
    if not MONGODB_AVAILABLE:
        pytest.skip("MongoDB not available; skipping agent integration test")


async def _fresh_db():
    from app.db import Database

    db = Database.get_db()
    for collection in ("financial_records", "reconciliation_cases", "reconciliation_runs",
                       "audit_events", "evidence_items", "ground_truth",
                       "synthetic_datasets", "agent_runs", "agent_events"):
        await db[collection].delete_many({})
    return db


async def test_executor_gates_by_policy_and_stages_rest():
    await _require_mongodb()
    db = await _fresh_db()

    from app.agent.executor import AgentExecutor
    from app.domain.cases import DeterministicInfo, Discrepancy

    low = ReconciliationCase(
        case_id="CASE_LOW",
        status=CaseStatus.EXCEPTION,
        risk=RiskLevel.LOW,
        amount=10000,
        currency="INR",
        record_type="payment",
        outcome_type="amount_mismatch",
        match_score=100.0,
        discrepancy=Discrepancy(amount_diff=0, currency="INR"),
        deterministic_info=DeterministicInfo(
            match_score=100.0,
            candidate_ids=[],
            reason_codes=["exact"],
            calculated_difference=0,
            tolerance_used=100,
            signal_values={},
            rules_triggered=[],
        ),
    )
    high = ReconciliationCase(
        case_id="CASE_HIGH",
        status=CaseStatus.EXCEPTION,
        risk=RiskLevel.HIGH,
        amount=5000,
        currency="INR",
        record_type="payment",
        outcome_type="amount_mismatch",
        match_score=50.0,
        discrepancy=Discrepancy(amount_diff=0, currency="INR"),
        deterministic_info=DeterministicInfo(
            match_score=50.0,
            candidate_ids=[],
            reason_codes=["conflicting_candidates"],
            calculated_difference=0,
            tolerance_used=100,
            signal_values={},
            rules_triggered=[],
        ),
    )

    for case in (low, high):
        await db.reconciliation_cases.insert_one(case.to_mongo())

    executor = AgentExecutor(session_id="agent-test")
    result = await executor.handle_mismatched_cases({})

    assert low.case_id in result["executed"], "LOW-risk policy-eligible case should auto-close"
    assert high.case_id in result["staged_for_human_review"], "HIGH-risk case should be staged"

    stored_low = await db.reconciliation_cases.find_one({"case_id": "CASE_LOW"})
    stored_high = await db.reconciliation_cases.find_one({"case_id": "CASE_HIGH"})
    assert stored_low["status"] == "AUTO_RESOLVED"
    assert stored_high["status"] == "HUMAN_REVIEW"
    assert stored_high.get("agent_note"), "Staged case should carry an agent explanation"
    assert stored_high.get("reviewer"), "Staged case should name the agent as reviewer"

    agent_events = await db.audit_events.find({}).to_list(length=100)
    types = {e["event_type"] for e in agent_events}
    assert "AGENT_AUTO_CLOSED" in types
    assert "AGENT_STAGED_FOR_REVIEW" in types


async def test_agent_run_persists_events():
    await _require_mongodb()
    db = await _fresh_db()

    from app.agent.supervisor import AgentSupervisor
    class _Exec:
        async def summary(self, args=None):
            return {"total_cases": 7}

    # Inject a fake LLM + fake executor so the run never touches Groq/Mongo-capable exec.
    supervisor = AgentSupervisor(session_id="run-test")
    # Override the executor's answer path by giving a summary-only executor.
    supervisor.executor = _Exec()
    async def _answer(q):
        return "There are 7 total cases."
    async def _classify(q):
        return AgentIntent.QUESTION
    supervisor._answer_question = _answer
    supervisor._classify_intent = _classify  # deterministic

    response = await supervisor.run("how many cases?")
    assert response.status.value == "COMPLETED"
    assert "7" in (response.answer or "")

    events = await db.agent_events.find({"run_id": response.run_id}).to_list(length=100)
    assert events, "Expected agent events to be persisted"
    types = {e["event_type"] for e in events}
    assert "INTENT_CLASSIFIED" in types
    assert "RUN_COMPLETED" in types

    stored = await db.agent_runs.find_one({"run_id": response.run_id})
    assert stored is not None
    assert stored["status"] == "COMPLETED"