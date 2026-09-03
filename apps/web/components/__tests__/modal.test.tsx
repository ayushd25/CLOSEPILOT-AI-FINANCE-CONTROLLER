import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";

import { Modal } from "@/components/ui/modal";

describe("Modal", () => {
  it("does not render when closed", () => {
    const onClose = vi.fn();
    const { container } = render(
      <Modal open={false} onClose={onClose} title="Details">
        <p>content</p>
      </Modal>,
    );
    expect(container.querySelector("[role='dialog']")).toBeNull();
  });

  it("renders title and children when open", () => {
    render(
      <Modal open onClose={() => {}} title="AI Investigation complete">
        <p>validation_status: valid</p>
      </Modal>,
    );
    expect(screen.getByText("AI Investigation complete")).toBeInTheDocument();
    expect(screen.getByText("validation_status: valid")).toBeInTheDocument();
  });

  it("calls onClose when the close button is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose} title="Error">
        <p>something failed</p>
      </Modal>,
    );
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});