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

Provide your analysis as structured output."""

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

        try:
            from langchain_core.output_parsers import PydanticOutputParser

            parser = PydanticOutputParser(pydantic_object=InvestigationProposal)

            llm = self._get_llm()
            chain = llm | parser

            # Run in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: chain.invoke(prompt))

            elapsed = (utcnow() - started).total_seconds() * 1000
            metadata.latency_ms = int(elapsed)
            metadata.validation_status = "valid"
            return result, metadata
        except Exception as e:
            elapsed = (utcnow() - started).total_seconds() * 1000
            metadata.latency_ms = int(elapsed)
            metadata.validation_status = "error"
            metadata.error = str(e)[:500]
            return None, metadata
