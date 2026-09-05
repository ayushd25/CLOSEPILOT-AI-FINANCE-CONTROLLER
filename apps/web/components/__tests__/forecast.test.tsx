import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

import ForecastPage from "@/app/forecast/page";

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal("ResizeObserver", ResizeObserverStub);

vi.mock("next/navigation", () => ({
  usePathname: () => "/forecast",
}));

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const apiGet = api.get as ReturnType<typeof vi.fn>;

const sample = {
  as_of: "2026-09-05T00:00:00Z",
  horizon_days: 7,
  currency: "INR",
  current_cash: 500000,
  inflow_expected: 150000,
  outflow_expected: 40000,
  risk_holdback: 25000,
  net_change: 110000,
  projected_optimistic: 610000,
  projected_cash: 585000,
  confidence: 0.82,
  data_quality: {
    days_of_history: 42,
    records_used: { payments: 60, settlements: 60, bank: 42 },
    settlement_lag_days: 1,
    refund_rate: 0.021,
    avg_daily_settlement: 21000,
    daily_volatility: 4200,
  },
  components: [
    { category: "SCHEDULED_SETTLEMENTS", label: "Scheduled settlements", amount: 120000, count: 35, detail: "35 settlement(s)", netted: false },
    { category: "RECEIVABLES", label: "Expected receivables", amount: 30000, count: 3, detail: "3 open receivable(s)", netted: false },
    { category: "EXPECTED_REFUNDS", label: "Expected refunds", amount: 40000, count: 8, detail: "8 refund(s) in flight", netted: false },
    { category: "RISK_HOLDBACK", label: "Risk holdback", amount: 25000, count: 1, detail: "Suspended from open cases", netted: true },
  ],
  points: [
    { date: "2026-09-06", projected_cash: 520000, risk_adjusted_cash: 514000, lower_bound: 490000, upper_bound: 555000 },
    { date: "2026-09-07", projected_cash: 545000, risk_adjusted_cash: 538000, lower_bound: 495000, upper_bound: 570000 },
    { date: "2026-09-08", projected_cash: 559000, risk_adjusted_cash: 551000, lower_bound: 500000, upper_bound: 580000 },
    { date: "2026-09-09", projected_cash: 572000, risk_adjusted_cash: 563000, lower_bound: 505000, upper_bound: 590000 },
    { date: "2026-09-10", projected_cash: 580000, risk_adjusted_cash: 571000, lower_bound: 510000, upper_bound: 598000 },
    { date: "2026-09-11", projected_cash: 590000, risk_adjusted_cash: 580000, lower_bound: 515000, upper_bound: 606000 },
    { date: "2026-09-12", projected_cash: 610000, risk_adjusted_cash: 585000, lower_bound: 520000, upper_bound: 615000 },
  ],
  assumptions: [
    "Settlements arrive after 1 day lag with the historical average size.",
  ],
  commentary: "Projected cash rises to INR 5,85,000 by day 7, driven by 35 scheduled settlements.",
};

describe("Forecast page", () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiGet.mockImplementation((path: string) =>
      path.includes("/forecast") ? Promise.resolve(sample) : Promise.resolve({}),
    );
  });

  it("renders headline metrics from API data", async () => {
    render(<ForecastPage />);
    expect(await screen.findByText("Current Cash")).toBeInTheDocument();
    expect(screen.getByText("₹5,000")).toBeInTheDocument();
    expect(screen.getByText(/Projected \(Conservative\)/)).toBeInTheDocument();
    expect(screen.getByText("₹5,850")).toBeInTheDocument();
  });

  it("renders the component breakdown, assumptions and AI commentary", async () => {
    render(<ForecastPage />);
    await screen.findByText("Inflows");
    expect(screen.getByText("Scheduled settlements")).toBeInTheDocument();
    expect(screen.getByText("Risk holdback")).toBeInTheDocument();
    expect(screen.getByText(/1 day lag/)).toBeInTheDocument();
    expect(screen.getByText(/INR 5,85,000/)).toBeInTheDocument();
  });

  it("shows an empty state when no history is loaded", async () => {
    apiGet.mockImplementation(() =>
      Promise.resolve({
        ...sample,
        current_cash: 0,
        points: [],
        data_quality: { ...sample.data_quality, days_of_history: 0 },
      }),
    );
    render(<ForecastPage />);
    expect(await screen.findByText(/No bank\/settlement history loaded/)).toBeInTheDocument();
  });
});