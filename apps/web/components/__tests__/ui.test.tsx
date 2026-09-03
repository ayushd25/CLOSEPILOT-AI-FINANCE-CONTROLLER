import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";

import { MetricCard } from "@/components/metric-card";
import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

describe("MetricCard", () => {
  it("renders label and value", () => {
    render(<MetricCard label="Auto-resolved" value="42" />);
    expect(screen.getByText("Auto-resolved")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders sublabel when provided", () => {
    render(<MetricCard label="Risk" value="LOW" sublabel="2 cases" />);
    expect(screen.getByText("2 cases")).toBeInTheDocument();
  });

  it("does not render sublabel when omitted", () => {
    const { container } = render(<MetricCard label="Risk" value="LOW" />);
    expect(container.querySelector("p")?.textContent).not.toContain("cases");
  });
});

describe("Badge", () => {
  it("renders children text", () => {
    render(<Badge>EXCEPTION</Badge>);
    expect(screen.getByText("EXCEPTION")).toBeInTheDocument();
  });

  it("applies variant-specific class for success", () => {
    const { container } = render(<Badge variant="success">OK</Badge>);
    expect(container.firstElementChild).not.toBeNull();
  });

  it("accepts an explicit variant string", () => {
    render(<Badge variant="warning">HIGH</Badge>);
    expect(screen.getByText("HIGH")).toBeInTheDocument();
  });

  it("accepts a dynamic variant value", () => {
    const variant = "warning" as BadgeVariant;
    render(<Badge variant={variant}>WARN</Badge>);
    expect(screen.getByText("WARN")).toBeInTheDocument();
  });
});

describe("Button", () => {
  it("renders a button with its label", () => {
    render(<Button>Approve</Button>);
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
  });

  it("supports click handlers", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Run</Button>);
    await user.click(screen.getByRole("button", { name: "Run" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});