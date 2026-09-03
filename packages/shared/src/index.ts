export type CaseStatus =
  | "UNPROCESSED"
  | "MATCHED"
  | "AUTO_RESOLVED"
  | "EXCEPTION"
  | "HUMAN_REVIEW"
  | "RESOLVED"
  | "REJECTED";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface ReconciliationCase {
  case_id: string;
  status: CaseStatus;
  risk: RiskLevel;
  match_score: number;
  outcome_type: string;
  amount: number;
  currency: string;
  related_record_ids: string[];
  source: string;
  record_type: string;
}

export interface DashboardSummary {
  total_records: number;
  total_cases: number;
  reconciled: number;
  auto_resolved: number;
  human_review: number;
  exceptions: number;
  precision: number;
  recall: number;
  false_auto_match_rate: number;
}

export type SourceType = "synthetic" | "system_calculation" | "human";

export type RecordType =
  | "payment"
  | "order"
  | "settlement"
  | "bank_transaction"
  | "invoice"
  | "fee"
  | "tax"
  | "refund"
  | "chargeback"
  | "adjustment";
