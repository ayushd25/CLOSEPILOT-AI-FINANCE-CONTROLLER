import asyncio

from app.utils import utcnow
from typing import Any, Optional

from app.ai.proposals import InvestigationMetadata, InvestigationProposal
from app.ai.tools import AIReadOnlyTools
from app.config import settings
from app.db import Database
from app.domain.cases import AIProposal, RiskLevel


class AIInvestigatorService:
    def __init__(self):
        self.db = Database.get_db()
        self.tools = AIReadOnlyTools()
        self._groq = None

    @property
    def is_configured(self) -> bool:
        return bool(settings.GROQ_API_KEY)

    def _get_llm(self):
        if self._groq is None:
            from langchain_groq import ChatGroq

            self._groq = ChatGroq(
                model=settings.GROQ_MODEL,
                temperature=settings.GROQ_TEMPERATURE,
                api_key=settings.GROQ_API_KEY,
            )
        return self._groq

    def _build_prompt(self, context: dict[str, Any]) -> str:
        return f"""You are ClosePilot's AI Finance Controller investigator.

You are investigating a financial reconciliation case. Your job is to:
1. Inspect the case data and related financial records
2. Determine what happened and why there's a discrepancy
3. Rank evidence that supports your conclusion
4. Propose an action and confidence/risk level
5. Identify missing evidence or unresolved questions

CRITICAL RULES:
- Never invent facts. Only use the data provided.
- Distinguish between facts (observed in data) and inferences (your reasoning).
- Cite evidence IDs for any conclusion you make.
- If you cannot determine what happened with high confidence, choose conclusion=INSUFFICIENT_EVIDENCE.
- Prefer "I don't know" over "probably right" when financial risk is material.
- Never propose auto-closing a case without sufficient evidence and low risk.
- You cannot directly mutate any data. You can only propose.

Case data:
{context['case']}

Related records:
{context['records']}

Available evidence:
{context['evidence']}

Policy requirements:
{context['policy']}

OUTPUT FORMAT: Respond with a SINGLE JSON object and nothing else. No prose, no
markdown code fences, no headings, no bullet lists, no trailing explanation.
The JSON object must contain EXACTLY these keys:
- "case_id": string (must equal the case id above)
- "conclusion": one of "INSUFFICIENT_EVIDENCE", "MATCH_CONFIRMED", "NO_MATCH", "EXPLAINED_DISCREPANCY"
- "root_cause": string or null (likely root cause of the discrepancy)
- "confidence": number between 0.0 and 1.0
- "risk_level": one of "LOW", "MEDIUM", "HIGH", "CRITICAL"
- "proposed_action": one of "AUTO_CLOSE", "KEEP_EXCEPTION", "MATCH", "RESOLVE", "REJECT"
- "evidence_ids": array of strings (evidence IDs that support your conclusion)
- "reason_codes": array of strings
- "unresolved_questions": array of strings

Example:
{{"case_id": "CASE_x", "conclusion": "INSUFFICIENT_EVIDENCE", "root_cause": null,
"confidence": 0.6, "risk_level": "HIGH", "proposed_action": "KEEP_EXCEPTION",
"evidence_ids": [], "reason_codes": ["conflicting_candidates"], "unresolved_questions": []}}"""

    async def investigate(self, case_id: str) -> tuple[Optional[InvestigationProposal], InvestigationMetadata]:
        started = utcnow()
        metadata = InvestigationMetadata(model=settings.GROQ_MODEL, request_timestamp=started, latency_ms=0)

        if not self.is_configured:
            metadata.validation_status = "unavailable"
            metadata.error = "Groq API key not configured"
            return None, metadata

        case_doc = await self.db.reconciliation_cases.find_one({"case_id": case_id})
        if not case_doc:
            metadata.error = f"Case {case_id} not found"
            metadata.validation_status = "error"
            return None, metadata

        records = await self.tools.get_related_records(case_id)
        evidence = await self.tools.get_evidence(case_id)
        policy = await self.tools.get_policy()

        context = {
            "case": case_doc,
            "records": records,
            "evidence": evidence,
            "policy": policy,
        }

        prompt = self._build_prompt(context)
        llm = self._get_llm()
        loop = asyncio.get_event_loop()

        # Primary path: this Groq free-tier model does not honour structured
        # output / tool calling (400 "model did not call a tool"). So we drive
        # it with a strict-JSON prompt and recover the JSON from the raw text
        # (tolerating accidental markdown fences/prose).
        try:
            raw = await loop.run_in_executor(None, lambda: llm.invoke(prompt))
            text = raw.content if hasattr(raw, "content") else str(raw)
            from app.ai.parsing import extract_json_object

            parsed = extract_json_object(text)
            result = InvestigationProposal.model_validate(parsed)
            elapsed = (utcnow() - started).total_seconds() * 1000
            metadata.latency_ms = int(elapsed)
            metadata.validation_status = "valid"
            return result, metadata
        except Exception as prim_exc:
            # Fallback: structured output through Groq's tool/JSON-schema path,
            # which works for models that DO support function calling.
            try:
                structured = llm.with_structured_output(InvestigationProposal)
                result = await loop.run_in_executor(None, lambda: structured.invoke(prompt))
                elapsed = (utcnow() - started).total_seconds() * 1000
                metadata.latency_ms = int(elapsed)
                metadata.validation_status = "valid"
                return result, metadata
            except Exception as fallback_err:
                elapsed = (utcnow() - started).total_seconds() * 1000
                metadata.latency_ms = int(elapsed)
                metadata.validation_status = "error"
                combined = f"{prim_exc} | fallback: {fallback_err}"
                metadata.error = str(combined)[:500]
                return None, metadata
