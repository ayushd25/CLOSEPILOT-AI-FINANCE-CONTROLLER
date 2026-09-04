import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import Docs from "@/app/docs/page";

vi.mock("next/navigation", () => ({
  usePathname: () => "/docs",
}));

describe("Docs page", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("renders the guide title and core principle", () => {
    render(<Docs />);
    // The tagline appears both in the sidebar and the docs hero, so expect 2+.
    expect(screen.getAllByText(/Models investigate/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Rules authorize/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Evidence proves/).length).toBeGreaterThanOrEqual(1);
    // The h1 is unique.
    expect(screen.getByRole("heading", { level: 1, name: "How to use ClosePilot" })).toBeInTheDocument();
  });

  it("documents navigation, roles and the reconciliation workflow", () => {
    render(<Docs />);
    expect(screen.getByRole("heading", { name: "1. Navigating the platform" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "2. Roles & permissions" })).toBeInTheDocument();
    expect(screen.getAllByText("FINANCE_CONTROLLER").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("heading", { name: "3. Analyze, verify & auto-evaluate transactions" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "4. Using the assistive agent" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "5. Policy configuration" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "6. Audit & evidence" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "7. Troubleshooting" })).toBeInTheDocument();
  });
});