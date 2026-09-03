from typing import Any, Optional

from app.db import Database
from app.domain.cases import ReconciliationCase
from app.domain.evidence import (
    EdgeType,
    EvidenceEdge,
    EvidenceGraph,
    EvidenceItem,
    EvidenceSource,
)
from app.domain.models import FinancialRecord


class EvidenceService:
    def __init__(self):
        self.db = Database.get_db()

    async def create_evidence(
        self,
        entity_type: str,
        entity_id: str,
        statement: str,
        source: EvidenceSource,
        extracted_value: Any = None,
        created_by: str = "system",
        case_id: Optional[str] = None,
    ) -> EvidenceItem:
        item = EvidenceItem(
            entity_type=entity_type,
            entity_id=entity_id,
            statement=statement,
            source=source,
            extracted_value=extracted_value,
            created_by=created_by,
            case_id=case_id,
        )
        result = await self.db.evidence_items.insert_one(item.to_mongo())
        item.evidence_id = str(result.inserted_id)
        return item

    async def get_evidence_for_entity(self, entity_type: str, entity_id: str) -> list[EvidenceItem]:
        cursor = self.db.evidence_items.find({"entity_type": entity_type, "entity_id": entity_id})
        docs = await cursor.to_list(length=1000)
        return [EvidenceItem.from_mongo(d) for d in docs]

    async def get_evidence_for_case(self, case_id: str) -> list[EvidenceItem]:
        cursor = self.db.evidence_items.find({"case_id": case_id})
        docs = await cursor.to_list(length=1000)
        return [EvidenceItem.from_mongo(d) for d in docs]

    async def get_graph(self, case: ReconciliationCase) -> EvidenceGraph:
        nodes: list[dict[str, Any]] = []
        edges: list[EvidenceEdge] = []
        seen_nodes: set[str] = set()

        for record_id in case.related_record_ids:
            for record_type in ("payment", "settlement", "bank_transaction", "order", "invoice", "fee", "tax", "refund", "chargeback", "adjustment"):
                doc = await self.db.financial_records.find_one({"record_type": record_type, "external_id": record_id})
                if doc and record_id not in seen_nodes:
                    seen_nodes.add(record_id)
                    rec = FinancialRecord.from_mongo(doc)
                    nodes.append({
                        "id": record_id,
                        "type": record_type,
                        "amount": rec.amount,
                        "currency": rec.currency,
                        "status": rec.status,
                        "source": rec.source.value,
                        "description": rec.description,
                    })

        # Define canonical relationships
        for i in range(len(case.related_record_ids) - 1):
            a = case.related_record_ids[i]
            a_doc = await self.db.financial_records.find_one({"external_id": a})
            b_doc = await self.db.financial_records.find_one({"external_id": case.related_record_ids[i + 1]})
            if a_doc and b_doc and a_doc["record_type"] != b_doc["record_type"]:
                edge_type = EdgeType.MATCHED_TO
                if a_doc["record_type"] == "settlement" and b_doc["record_type"] == "bank_transaction":
                    edge_type = EdgeType.SETTLED_AS
                if a_doc["record_type"] == "payment" and b_doc["record_type"] == "settlement":
                    edge_type = EdgeType.MATCHED_TO
                edges.append(EvidenceEdge(source=a, target=case.related_record_ids[i + 1], edge_type=edge_type))

        for cand in case.candidate_matches:
            cand_id = cand.get("external_id")
            if cand_id and cand_id not in seen_nodes:
                doc = await self.db.financial_records.find_one({"external_id": cand_id})
                if doc:
                    seen_nodes.add(cand_id)
                    rec = FinancialRecord.from_mongo(doc)
                    nodes.append({
                        "id": cand_id,
                        "type": rec.record_type,
                        "amount": rec.amount,
                        "currency": rec.currency,
                        "status": rec.status,
                        "source": rec.source.value,
                        "description": rec.description,
                    })
                    edges.append(EvidenceEdge(
                        source=str(case.related_record_ids[0]) if case.related_record_ids else "",
                        target=cand_id,
                        edge_type=EdgeType.CONFLICTS_WITH,
                        label=f"score {cand.get('score', 0):.1f}",
                    ))

        return EvidenceGraph(nodes=nodes, edges=edges)
