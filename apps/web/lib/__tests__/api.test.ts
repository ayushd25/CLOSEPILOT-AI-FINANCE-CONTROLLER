import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

import { HttpClient } from "@/lib/api";

function listenFor(wait = 50): Promise<{
  method: string;
  path: string;
  message: string;
}> {
  return new Promise((resolve, reject) => {
    const handler = (e: Event) => {
      window.removeEventListener("closepilot:api-error", handler);
      resolve((e as CustomEvent).detail);
    };
    window.addEventListener("closepilot:api-error", handler);
    setTimeout(() => {
      window.removeEventListener("closepilot:api-error", handler);
      reject(new Error("no global API error event dispatched"));
    }, wait);
  });
}

describe("HttpClient", () => {
  const originalFetch = global.fetch;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    localStorage.clear();
    fetchMock = vi.fn();
    global.fetch = fetchMock as unknown as typeof fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("builds GET requests with base URL and role header", async () => {
    localStorage.setItem("closepilot_role", "REVIEWER");
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    } as Response);

    const client = new HttpClient("http://test.local");
    await client.get("/health");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://test.local/health");
    expect(init.method).toBe("GET");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.headers["X-User-Role"]).toBe("REVIEWER");
    expect(init.cache).toBe("no-store");
  });

  it("defaults role to FINANCE_CONTROLLER when no role stored", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    } as Response);

    const client = new HttpClient("http://test.local");
    await client.get("/x");

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers["X-User-Role"]).toBe("FINANCE_CONTROLLER");
  });

  it("serializes JSON body on POST", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ id: 1 }),
    } as Response);

    const client = new HttpClient("http://test.local");
    const result = await client.post<{ id: number }>("/cases/1/approve", { note: "ok" });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ note: "ok" });
    expect(result).toEqual({ id: 1 });
  });

  it("throws a descriptive error on non-ok responses", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 403,
      text: async () => "forbidden payload",
    } as Response);

    const client = new HttpClient("http://test.local");
    await expect(client.get("/cases/1/policy")).rejects.toThrow(
      "API error 403: forbidden payload"
    );
  });

  it("defaults base URL when none provided", () => {
    const client = new HttpClient();
    expect(client).toBeDefined();
  });

  it("dispatches a global error event on network failure", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    const listener = listenFor();
    const client = new HttpClient("http://test.local");
    await expect(client.get("/health")).rejects.toThrow("API network error");
    const detail = await listener;
    expect(detail.method).toBe("GET");
    expect(detail.path).toBe("/health");
    expect(detail.message).toContain("Failed to fetch");
  });

  it("dispatches a global error event on 5xx responses, but not on 4xx", async () => {
    // 4xx should not trigger the global modal (page-level handling owns it)
    fetchMock.mockResolvedValue({
      ok: false,
      status: 404,
      text: async () => "not found",
    } as Response);
    const client4xx = new HttpClient("http://test.local");
    await expect(client4xx.get("/cases/1")).rejects.toThrow("API error 404");

    // 5xx should trigger the global modal
    fetchMock.mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => "boom",
    } as Response);
    const listener = listenFor();
    await expect(client4xx.get("/boom")).rejects.toThrow("API error 500");
    const detail = await listener;
    expect(detail.message).toContain("API error 500");
    expect(detail.path).toBe("/boom");
  });
});