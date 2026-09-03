import { describe, it, expect } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";

import {
  GlobalErrorProvider,
  GLOBAL_API_ERROR_EVENT,
} from "@/components/global-error-provider";

function dispatchError(overrides: Partial<{ method: string; path: string; message: string }> = {}) {
  act(() => {
    window.dispatchEvent(
      new CustomEvent(GLOBAL_API_ERROR_EVENT, {
        detail: {
          method: "GET",
          path: "/health",
          message: "Failed to fetch",
          ...overrides,
        },
      }),
    );
  });
}

describe("GlobalErrorProvider", () => {
  it("renders children and no modal by default", () => {
    const { container } = render(
      <GlobalErrorProvider>
        <p>page</p>
      </GlobalErrorProvider>,
    );
    expect(screen.getByText("page")).toBeInTheDocument();
    expect(container.querySelector("[role='dialog']")).toBeNull();
  });

  it("shows a modal when an API error event is dispatched", async () => {
    render(
      <GlobalErrorProvider>
        <p>page</p>
      </GlobalErrorProvider>,
    );
    dispatchError();
    await screen.findByText("Backend unreachable");
    expect(screen.getByText("Failed to fetch")).toBeInTheDocument();
  });

  it("warns about the backend for network failures", async () => {
    render(
      <GlobalErrorProvider>
        <p>page</p>
      </GlobalErrorProvider>,
    );
    dispatchError({ message: "TypeError: Failed to fetch" });
    await screen.findByText(/docker compose up -d/);
  });

  it("closes the modal when the close button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <GlobalErrorProvider>
        <p>page</p>
      </GlobalErrorProvider>,
    );
    dispatchError();
    await screen.findByText("Backend unreachable");
    await user.click(screen.getByRole("button", { name: "Close" }));
    await screen.findByText("page");
    expect(screen.queryByText("Backend unreachable")).toBeNull();
  });

  it("does not crash when dispatched with no detail", () => {
    render(
      <GlobalErrorProvider>
        <p>page</p>
      </GlobalErrorProvider>,
    );
    act(() => {
      window.dispatchEvent(new CustomEvent(GLOBAL_API_ERROR_EVENT, {}));
    });
    expect(screen.getByText("page")).toBeInTheDocument();
  });
});