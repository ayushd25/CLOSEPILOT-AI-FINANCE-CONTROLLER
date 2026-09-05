import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import TaxPage from "@/app/tax/page";

vi.mock("next/navigation", () => ({
  usePathname: () => "/tax",
}));

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const apiGet = api.get as ReturnType<typeof vi.fn>;
const apiPost = api.post as ReturnType<typeof vi.fn>;

const match = {
  match_id: "TXM_pay_1_TAX_1",
  tax_line_id: "TAX_1001",
  reference: "INV_1001",
  transaction_id: "pay_1",
  invoice_id: "INV_1001",
  currency: "INR",
  gross_amount: 118000,
  taxable_amount: 100000,
  tax_rate: 18,
  expected_tax: 18000,
  recorded_tax: 18000,
  difference: 0,
  tolerance: 100,
  fee_amount: 0,
  status: "VERIFIED",
  reason_codes: [],
  calculation: "expected_tax = round(100000 x 18 / 100) = 18000; recorded 18000; difference 0",
  related_record_ids: ["PAY_pay_1", "STL_SET_1", "TAX_TAX_1001"],
  evidence_ids: ["EVID_1", "EVID_2"],
  case_id: null,
  ai_analysis: null,
  confidence: 1.0,
  created_at: "2026-09-05T00:00:00Z",
  updated_at: "2026-09-05T00:00:00Z",
  reviewed_by: null,
  review_note: null,
};

describe("Tax matcher page", () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPost.mockReset();
    apiGet.mockImplementation((path: string) => {
      if (path.includes("/tax-lines/metrics"))
        return Promise.resolve({ checked: 12, verified: 9, exceptions: 2, human_review: 1, match_rate: 0.75 });
      if (path.includes("/tax-lines?"))
        return Promise.resolve({ total: 1, matches: [match] });
      if (path.includes("/tax-lines/"))
        return Promise.resolve(match);
      return Promise.resolve({});
    });
  });

  it("renders metrics and the matched lines table", async () => {
    render(<TaxPage />);
    expect(await screen.findByText("Lines Checked")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("pay_1")).toBeInTheDocument();
    expect(screen.getAllByText("VERIFIED").length).toBeGreaterThanOrEqual(1);
  });

  it("opens a detail modal with the calculation and evidence", async () => {
    render(<TaxPage />);
    fireEvent.click(await screen.findByText("pay_1"));
    expect(await screen.findByText("Calculation")).toBeInTheDocument();
    expect(screen.getByText(/expected_tax = round/)).toBeInTheDocument();
    expect(screen.getByText("EVID_1")).toBeInTheDocument();
  });

  it("runs the matcher via POST and shows the summary banner", async () => {
    apiPost.mockResolvedValue({ processed: 12, skipped: 0, verified: 9, exceptions: 2, human_review: 1 });
    render(<TaxPage />);
    fireEvent.click(screen.getByRole("button", { name: /Run matcher/ }));
    expect(await screen.findByText(/Run complete — 12 line\(s\) checked/)).toBeInTheDocument();
    expect(apiPost).toHaveBeenCalledWith("/reconciliation/tax-lines/run?ai=false");
  });
});