import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

import { HttpClient } from "@/lib/api";

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
});