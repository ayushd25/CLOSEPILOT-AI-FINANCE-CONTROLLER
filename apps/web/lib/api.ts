const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

declare global {
  interface WindowEventMap {
    "closepilot:api-error": CustomEvent<{
      method: string;
      path: string;
      message: string;
    }>;
  }
}

export interface ApiClient {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body?: unknown): Promise<T>;
}

function reportGlobalError(method: string, path: string, message: string) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("closepilot:api-error", {
      detail: { method, path, message },
    }),
  );
}

export class HttpClient implements ApiClient {
  private baseUrl: string;

  constructor(baseUrl = API_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    let res: Response;
    try {
      res = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          "X-User-Role": localStorage.getItem("closepilot_role") || "FINANCE_CONTROLLER",
        },
        body: body ? JSON.stringify(body) : undefined,
        cache: "no-store",
      });
    } catch (e) {
      // Network-level failure: backend unreachable, DNS, connection refused, etc.
      const message = e instanceof Error ? e.message : String(e);
      reportGlobalError(method, path, message);
      throw new Error(`API network error: ${message}`);
    }

    if (!res.ok) {
      const text = await res.text();
      const message = `API error ${res.status}: ${text.slice(0, 200)}`;
      if (res.status >= 500) {
        reportGlobalError(method, path, message);
      }
      throw new Error(message);
    }
    return res.json() as Promise<T>;
  }

  get<T>(path: string) {
    return this.request<T>("GET", path);
  }

  post<T>(path: string, body?: unknown) {
    return this.request<T>("POST", path, body);
  }
}

export const api = new HttpClient();
