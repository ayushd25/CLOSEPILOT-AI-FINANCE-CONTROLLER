import asyncio
import json
import re
from typing import Any
from uuid import uuid4

from app.ai.parsing import extract_json_object
from app.agent.executor import AgentExecutor, AgentToolError, TOOL_REGISTRY, get_tool_help
from app.agent.help import platform_help
from app.config import settings
from app.db import Database
from app.domain.agent import (
    AgentEvent,
    AgentIntent,
    AgentPlanStep,
    AgentResponse,
    AgentRun,
    AgentRunStatus,
    AgentToolCall,
)
from app.utils import utcnow


class AgentSupervisor:
    """Routes a request to Q&A or task execution.

    - Q&A: answers from live platform data (read-only), never mutating.
    - TASK: builds a plan and executes it through the authorised executor,
      which keeps the PolicyEngine as the final authorisation gate.

    Progress is persisted to `agent_runs` + `agent_events` so the UI can
    stream a live plan/progress panel.
    """

    def __init__(self, session_id: str | None = None, role: str = "FINANCE_CONTROLLER"):
        self.db = Database.get_db()
        self.session_id = session_id or str(uuid4())
        self.role = role
        self.executor = AgentExecutor(session_id=self.session_id, role=role)
        self._llm = None

    @property
    def is_configured(self) -> bool:
        return bool(settings.GROQ_API_KEY)

    def _get_llm(self):
        if self._llm is None:
            from langchain_groq import ChatGroq

            self._llm = ChatGroq(
                model=settings.GROQ_MODEL,
                temperature=settings.GROQ_TEMPERATURE,
                api_key=settings.GROQ_API_KEY,
            )
        return self._llm

    async def run(self, request_text: str) -> AgentResponse:
        run = AgentRun(
            run_id=str(uuid4()),
            session_id=self.session_id,
            request_text=request_text,
            intent=AgentIntent.QUESTION,
            status=AgentRunStatus.RUNNING,
        )
        await self._insert_run(run)
        await self.event(run, "RUN_STARTED", f"Agent session started for: {request_text}")

        try:
            intent = await self._classify_intent(request_text)
        except Exception:
            intent = AgentIntent.QUESTION

        run.intent = intent
        await self.event(run, "INTENT_CLASSIFIED", f"Intent classified as {intent.value}")
        await self._update_run(run)

        try:
            if intent == AgentIntent.TASK:
                answer = await self._execute_task(run, request_text)
            else:
                answer = await self._answer_question(request_text)
        except Exception as e:
            run.status = AgentRunStatus.FAILED
            run.answer = f"Agent failed: {e}"
            run.completed_at = utcnow()
            await self._update_run(run)
            await self.event(run, "RUN_FAILED", f"Agent run failed: {e}")
            return await self._finish(run)

        run.status = AgentRunStatus.COMPLETED
        run.answer = answer
        run.completed_at = utcnow()
        await self._update_run(run)
        await self.event(run, "RUN_COMPLETED", f"Agent completed ({run.executed_actions} executed, {run.staged_actions} staged)")
        return await self._finish(run)

    # ------------------------------------------------------------------ #
    # Q&A                                                                #
    # ------------------------------------------------------------------ #
    async def _answer_question(self, question: str) -> str:
        # Build context: platform guide (for general/how-to questions) plus the
        # aggregate summary and any specific cases referenced in the question.
        parts: list[str] = []
        parts.append("PLATFORM GUIDE (use for 'what can I do', 'how do I', general questions):\n" + platform_help())

        summary = await self.executor.summary()
        parts.append("PLATFORM SUMMARY:\n" + json.dumps(summary, default=str))

        case_ids = set(re.findall(r"CASE_[A-Za-z0-9_]+", question))
        for cid in list(case_ids)[:5]:
            try:
                detail = await self.executor.get_case({"case_id": cid})
                context = self._case_explainer(detail)
                if context:
                    parts.append(f"CASE DETAIL {cid}:\n" + context)
            except AgentToolError:
                parts.append(f"CASE DETAIL {cid}:\n(case not found)")

        context = "\n\n".join(parts)
        prompt = f"""You are ClosePilot's finance assistant. Use the PLATFORM GUIDE to answer general questions about what the platform is, how to navigate it, what you can do, and how to perform each task (reconciliation, investigation, policy evaluation, running the agent, etc.). Use the PLATFORM SUMMARY and CASE DETAIL blocks (live data) to answer questions about the current state or specific cases — be specific, explain root causes, and state why a case is risky (refer to its risk level, amount/impact, confidence, discrepancy, candidate conflicts). Do not invent facts beyond the guide and the data provided.

Platform data:
{context}

User question:
{question}

OUTPUT FORMAT: Respond with a single JSON object: {{"answer": "..."}}. No markdown fences, no prose outside the JSON."""
        raw = await self._invoke(prompt)
        text = raw.content if hasattr(raw, "content") else str(raw)
        parsed = extract_json_object(text)
        if not isinstance(parsed, dict) or "answer" not in parsed:
            raise ValueError("LLM response did not contain an answer")
        return str(parsed["answer"])

    def _case_explainer(self, case: dict) -> str:
        """Render a case so the LLM can reason about it in detail."""
        lines = [
            f"Case ID: {case.get('case_id')}",
            f"Status: {case.get('status')}",
            f"Risk level: {case.get('risk')}",
            f"Outcome type: {case.get('outcome_type')}",
            f"Record type: {case.get('record_type')}",
            f"Amount: {case.get('amount')} {case.get('currency')} (minor units)",
            f"Match score: {case.get('match_score')}",
            f"Related records: {case.get('related_record_ids')}",
        ]
        disc = case.get("discrepancy")
        if isinstance(disc, dict):
            lines.append(
                f"Discrepancy amount diff: {disc.get('amount_diff')} {disc.get('currency')}; detail: {disc.get('detail')}"
            )
        di = case.get("deterministic_info")
        if isinstance(di, dict):
            lines.append(f"Rules triggered: {di.get('rules_triggered')}")
            lines.append(f"Calculated difference: {di.get('calculated_difference')}")
            lines.append(f"Tolerance used: {di.get('tolerance_used')}")
            lines.append(f"Reason codes: {di.get('reason_codes')}")
        ai = case.get("ai_proposal")
        if isinstance(ai, dict):
            lines.append(f"AI conclusion: {ai.get('conclusion')}; confidence: {ai.get('confidence')}")
            lines.append(f"AI proposed action: {ai.get('proposed_action')}; risk: {ai.get('risk_level')}")
            lines.append(f"AI reason codes: {ai.get('reason_codes')}")
        if case.get("agent_note"):
            lines.append(f"Agent note: {case.get('agent_note')}")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Task execution                                                      #
    # ------------------------------------------------------------------ #
    async def _execute_task(self, run: AgentRun, task: str) -> str:
        plan = await self._plan(task)
        run.plan = plan
        await self._update_run(run)
        await self.event(
            run,
            "PLAN_CREATED",
            "Plan created: " + "; ".join(f"step{i.step}: {i.action}" for i in plan),
            data={"plan": [s.model_dump() for s in plan]},
        )

        for step in plan:
            await self.event(run, "STEP_STARTED", f"Executing step {step.step}: {step.action}", tool=step.tool, step=step.step)
            try:
                result = await self._call_tool(step)
                self._reflect_run_counters(run, step, result)
                await self._update_run(run)
                summary_text = self._summarize(result)
                step.status = "done"
                step.result_summary = summary_text
                await self.event(
                    run,
                    "STEP_COMPLETED",
                    f"Step {step.step} done: {summary_text}",
                    tool=step.tool,
                    step=step.step,
                    data={"result": result},
                )
            except Exception as e:
                step.status = "failed"
                step.message = str(e)
                await self.event(
                    run,
                    "STEP_FAILED",
                    f"Step {step.step} failed: {e}",
                    tool=step.tool,
                    step=step.step,
                )
                return f"Task partially completed. A step failed: {e}. Progress: {self._progress(run)}"
        run.plan = [s.model_dump() for s in plan]
        await self._update_run(run)
        return self._final_answer(run, plan)

    def _reflect_run_counters(self, run: AgentRun, step: AgentPlanStep, result: dict[str, Any]) -> None:
        if step.tool != "handle_mismatched_cases":
            if step.tool == "investigate_cases":
                run.executed_actions += int(result.get("investigated", 0))
            return
        run.executed_actions += len(result.get("executed") or [])
        run.staged_actions += len(result.get("staged_for_human_review") or [])
        run.denied_actions += len(result.get("denied") or [])

    async def _call_tool(self, step: AgentPlanStep) -> dict[str, Any]:
        tool = getattr(self.executor, step.tool, None)
        if tool is None:
            raise ValueError(f"unknown tool: {step.tool}")
        result = await tool(step.args)
        return result if isinstance(result, dict) else {"result": result}

    def _summarize(self, result: dict[str, Any]) -> str:
        parts: list[str] = []
        if "executed" in result and isinstance(result["executed"], list):
            parts.append(f"{len(result['executed'])} auto-closed")
        if "staged_for_human_review" in result and isinstance(result["staged_for_human_review"], list):
            parts.append(f"{len(result['staged_for_human_review'])} staged for review")
        if "processed" in result:
            parts.append(f"{result['processed']} processed")
        if "investigated" in result:
            parts.append(f"{result['investigated']} investigated")
        if not parts:
            parts.append(str(result)[:120])
        return "; ".join(parts) or "done"

    def _progress(self, run: AgentRun) -> str:
        return (
            f"executed={run.executed_actions} staged={run.staged_actions} "
            f"denied={run.denied_actions} plan_steps={len(run.plan)}"
        )

    def _final_answer(self, run: AgentRun, plan: list[AgentPlanStep]) -> str:
        done = [s for s in plan if s.status != "failed"]
        parts = []
        for s in done:
            parts.append(f"Step {s.step} ({s.action}): {s.result_summary}")
        executed = run.executed_actions
        staged = run.staged_actions
        return "\n".join(
            ([f"Completed {len(done)} of {len(plan)} steps."] if plan else [])
            + parts
            + [
                f"{executed} case(s) auto-closed through policy; {staged} staged for human review. "
                "Nothing was forced: only policy-eligible cases were mutated."
            ]
        )

    async def _plan(self, task: str) -> list[AgentPlanStep]:
        tools = get_tool_help()
        prompt = f"""You are ClosePilot's finance agent planner. The user gave a task. Decide the ordered steps to accomplish it.

Available tools:
{tools}

Important: `handle_mismatched_cases` is the tool that "handles all mismatched/open transactions" (auto-resolves policy-eligible ones, stages others for human review). `investigate_cases` runs AI investigations (proposals only).

User task:
{task}

OUTPUT FORMAT: Respond with a single JSON object:
{{"steps": [{{"action": "...", "tool": "tool_name", "args": {{...}}}}]}}
Choose 1-3 steps. No markdown fences, no prose outside the JSON."""
        raw = await self._invoke(prompt)
        text = raw.content if hasattr(raw, "content") else str(raw)
        parsed = extract_json_object(text)
        steps = parsed.get("steps") if isinstance(parsed, dict) else None
        if not isinstance(steps, list) or not steps:
            raise ValueError("planner returned no steps")
        out: list[AgentPlanStep] = []
        known = set(TOOL_REGISTRY)
        for i, s in enumerate(steps, start=1):
            if not isinstance(s, dict) or "tool" not in s or "action" not in s:
                raise ValueError("malformed plan step")
            tool = str(s["tool"])
            if tool not in known:
                raise ValueError(f"unknown tool in plan: {tool}")
            out.append(
                AgentPlanStep(
                    step=i,
                    action=str(s.get("action")),
                    tool=tool,
                    args=s.get("args") or {},
                )
            )
        return out

    async def _classify_intent(self, text: str) -> AgentIntent:
        prompt = f"""You classify user messages for a finance app into exactly one label:
- QUESTION: the user is asking a question, seeks information, or requests an explanation/status.
- TASK: the user wants you to DO something (handle, resolve, fix, close, process, investigate, run, reconcile, review, clear transactions/cases).

Message: "{text}"

OUTPUT FORMAT: A single JSON object: {{"intent": "QUESTION"}} or {{"intent": "TASK"}}. No other text."""
        raw = await self._invoke(prompt)
        text_out = raw.content if hasattr(raw, "content") else str(raw)
        parsed = extract_json_object(text_out)
        val = (parsed.get("intent") if isinstance(parsed, dict) else None) or ""
        return AgentIntent.TASK if val.upper().startswith("T") else AgentIntent.QUESTION

    async def _invoke(self, prompt: str):
        loop = asyncio.get_event_loop()
        llm = self._get_llm()
        return await loop.run_in_executor(None, lambda: llm.invoke(prompt))

    # ------------------------------------------------------------------ #
    # Persistence                                                        #
    # ------------------------------------------------------------------ #
    async def _insert_run(self, run: AgentRun) -> None:
        await self.db.agent_runs.insert_one(run.to_mongo())

    async def _update_run(self, run: AgentRun) -> None:
        doc = run.to_mongo()
        doc.pop("run_id", None)

        def _is_datum(d):
            from datetime import datetime
            return isinstance(d, (dict, list, float, int, str, bool)) or d is None or isinstance(d, datetime)

        def _clean(value):
            if isinstance(value, dict):
                return {k: _clean(v) for k, v in value.items() if _is_datum(_clean(v))}
            if isinstance(value, list):
                return [_clean(v) for v in value if _is_datum(_clean(v))]
            return value

        await self.db.agent_runs.update_one({"run_id": run.run_id}, {"$set": _clean(doc)})

    async def event(self, run: AgentRun, event_type: str, message: str, tool: str | None = None, step: int | None = None, data: dict | None = None) -> None:
        ev = AgentEvent(
            event_id=str(uuid4()),
            run_id=run.run_id,
            event_type=event_type,
            message=message,
            tool=tool,
            step=step,
            data=data,
        )
        await self.db.agent_events.insert_one(ev.to_mongo())

    async def _finish(self, run: AgentRun) -> AgentResponse:
        events = await self.get_events(run.run_id)
        return AgentResponse(
            run_id=run.run_id,
            intent=run.intent,
            status=run.status,
            answer=run.answer,
            events=events,
            summary={
                "executed": run.executed_actions,
                "staged": run.staged_actions,
                "denied": run.denied_actions,
                "plan_steps": len(run.plan),
            },
        )

    async def get_events(self, run_id: str, limit: int = 100) -> list[AgentEvent]:
        cursor = self.db.agent_events.find({"run_id": run_id}).sort("created_at", 1).limit(limit)
        return [AgentEvent.from_mongo(d) for d in await cursor.to_list(length=limit)]

    async def get_run(self, run_id: str) -> AgentRun:
        doc = await self.db.agent_runs.find_one({"run_id": run_id})
        if not doc:
            raise LookupError(f"run not found: {run_id}")
        return AgentRun.from_mongo(doc)