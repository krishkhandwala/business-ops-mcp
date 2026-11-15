const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class NexusApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== "undefined") {
      if (token) {
        window.localStorage.setItem("nexus_access_token", token);
      } else {
        window.localStorage.removeItem("nexus_access_token");
      }
    }
  }

  getToken(): string | null {
    if (this.token) return this.token;
    if (typeof window !== "undefined") {
      this.token = window.localStorage.getItem("nexus_access_token");
    }
    return this.token;
  }

  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };
    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errDetail = `Request failed (${res.status})`;
      try {
        const body = await res.json();
        errDetail = body.detail || errDetail;
      } catch {
        // ignore JSON parse error
      }
      throw new Error(errDetail);
    }

    return res.json() as Promise<T>;
  }
}

export const apiClient = new NexusApiClient();

