const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ApiClient {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body?: unknown): Promise<T>;
}

export class HttpClient implements ApiClient {
  private baseUrl: string;

  constructor(baseUrl = API_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-User-Role": localStorage.getItem("closepilot_role") || "FINANCE_CONTROLLER",
      },
      body: body ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`API error ${res.status}: ${text.slice(0, 200)}`);
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
