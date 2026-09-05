import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import Landing from "@/app/page";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const apiGet = api.get as ReturnType<typeof vi.fn>;

describe("Landing page", () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiGet.mockImplementation((path: string) => {
      if (path.includes("/dashboard/summary"))
        return Promise.resolve({
          total_records: 120,
          reconciled: 100,
          auto_resolved: 80,
          human_review: 4,
          exceptions: 2,
        });
      if (path.includes("/forecast?"))
        return Promise.resolve({ current_cash: 500000, projected_cash: 525000, horizon_days: 7 });
      if (path.includes("/tax-lines/metrics"))
        return Promise.resolve({ checked: 20, verified: 16, exceptions: 3 });
      return Promise.resolve({});
    });
  });

  it("renders the hero, principle and primary CTA", () => {
    render(<Landing />);
    expect(screen.getAllByRole("heading", { name: /Automate what you can prove/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Models investigate\. Rules authorize\. Evidence proves\./i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows live metrics once data loads", async () => {
    render(<Landing />);
    await screen.findByText("Records ingested");
    await waitFor(() => {
      expect(screen.getByText("120")).toBeInTheDocument();
    });
    expect(screen.getAllByText("Auto-resolved").length).toBeGreaterThanOrEqual(1);
  });

  it("offers a dataset call-to-action when the backend has no data", async () => {
    apiGet.mockImplementation(() => Promise.resolve({}));
    render(<Landing />);
    expect(await screen.findByText(/No data loaded yet/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Generate a dataset/i })).toBeInTheDocument();
  });
});