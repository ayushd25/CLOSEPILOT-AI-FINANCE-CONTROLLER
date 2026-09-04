import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

import Policies from "@/app/policies/page";

vi.mock("next/navigation", () => ({
  usePathname: () => "/policies",
}));

const defaultConfig = {
  version: 3,
  enabled: true,
  thresholds: {
    confidence_threshold: 0.7,
    max_auto_tolerance: 200,
    high_impact_threshold: 5000000,
    min_evidence_ids: 2,
    auto_close_match_score: 100,
  },
  toggles: {
    enforce_high_impact_gate: true,
    auto_close_medium_risk: false,
    auto_close_high_risk: false,
    enforce_multi_candidate_gate: true,
    enforce_discrepancy_tolerance: true,
    require_low_risk_for_deterministic_auto_close: true,
  },
  updated_at: "2026-01-01T00:00:00Z",
  updated_by: "admin",
  change_note: "initial",
};

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const apiGet = api.get as ReturnType<typeof vi.fn>;
const apiPut = api.put as ReturnType<typeof vi.fn>;

describe("Policies page", () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPut.mockReset();
    window.localStorage.clear();
    localStorage.setItem("closepilot_role", "FINANCE_CONTROLLER");
    apiGet.mockImplementation((path: string) => {
      if (path === "/policy") return Promise.resolve(defaultConfig);
      if (path === "/policy/defaults") return Promise.resolve(defaultConfig);
      return Promise.resolve({});
    });
  });

  it("loads and renders the current thresholds", async () => {
    render(<Policies />);
    expect(await screen.findByDisplayValue("0.7")).toBeInTheDocument();
    expect(screen.getByDisplayValue("200")).toBeInTheDocument();
    expect(screen.getByText("Allow medium-risk auto-close")).toBeInTheDocument();
  });

  it("saves edits via PUT and shows the resulting version", async () => {
    apiPut.mockResolvedValue({
      config: { ...defaultConfig, version: 4 },
      changes: [{ field: "confidence_threshold", from: 0.7, to: 0.8 }],
      version: 4,
    });

    render(<Policies />);
    const input = await screen.findByDisplayValue("0.7");
    fireEvent.change(input, { target: { value: "0.8" } });

    fireEvent.change(screen.getByPlaceholderText("e.g. Relax tolerance for settlement fee cases"), {
      target: { value: "Raise confidence" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Save & Apply/ }));

    await waitFor(() => {
      expect(apiPut).toHaveBeenCalledWith(
        "/policy",
        expect.objectContaining({
          thresholds: expect.objectContaining({ confidence_threshold: 0.8 }),
        }),
      );
    });
    expect(await screen.findByText(/version 4/)).toBeInTheDocument();
  });
});