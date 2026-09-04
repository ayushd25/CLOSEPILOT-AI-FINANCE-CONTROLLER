import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";

import AssistantWidget from "@/components/assistant/assistant-widget";

vi.mock("@/lib/api", () => ({
  api: {
    post: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const apiPost = api.post as ReturnType<typeof vi.fn>;

describe("AssistantWidget", () => {
  beforeEach(() => {
    window.localStorage.clear();
    apiPost.mockReset();
  });

  it("renders a closed toggle button by default", () => {
    render(<AssistantWidget />);
    expect(screen.getByRole("button", { name: "Open assistant" })).toBeInTheDocument();
  });

  it("opens the panel and lets the user send a message and see a reply", async () => {
    const user = userEvent.setup();
    apiPost.mockResolvedValue({
      run_id: "run-1",
      intent: "QUESTION",
      status: "COMPLETED",
      answer: "There are 12 open exceptions.",
    });

    render(<AssistantWidget />);
    await user.click(screen.getByRole("button", { name: "Open assistant" }));

    await user.type(screen.getByPlaceholderText("Ask or command the agent…"), "how many open exceptions?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("There are 12 open exceptions.")).toBeInTheDocument();
    expect(apiPost).toHaveBeenCalledWith("/agent/chat", {
      request: "how many open exceptions?",
      session_id: expect.any(String),
      role: "FINANCE_CONTROLLER",
    });
  });

  it("shows summary counts for task actions", async () => {
    const user = userEvent.setup();
    apiPost.mockResolvedValue({
      run_id: "run-2",
      intent: "TASK",
      status: "COMPLETED",
      answer: "Completed.",
      summary: { executed: 3, staged: 2 },
    });

    render(<AssistantWidget />);
    await user.click(screen.getByRole("button", { name: "Open assistant" }));
    await user.type(screen.getByPlaceholderText("Ask or command the agent…"), "handle mismatches");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Completed.")).toBeInTheDocument();
    expect(screen.getByText(/Auto-closed: 3/)).toBeInTheDocument();
    expect(screen.getByText(/Staged for human: 2/)).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    const user = userEvent.setup();
    apiPost.mockRejectedValue(new Error("boom"));

    render(<AssistantWidget />);
    await user.click(screen.getByRole("button", { name: "Open assistant" }));
    await user.type(screen.getByPlaceholderText("Ask or command the agent…"), "do something");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText(/Request failed: boom/)).toBeInTheDocument();
  });
});