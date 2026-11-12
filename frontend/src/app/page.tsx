const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:5000").replace(/\/$/, "") + "/api";

export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    return response.ok;
  } catch {
    return false;
  }
}

export type RoutingResult = {
  route: string;
  priority: string;
  reasons: string[];
  diagnosis: null;
  decision_support_only: true;
  requires_clinician_review: true;
  confidence?: number;
  recommended_specialist?: string;
  audit_hash?: string;
  biomechanics?: {
    landmark_count: number;
    normalized_path_length: number;
    interpretation: string;
  };
};

export async function apiRequest<T>(path: string, token?: string, body?: unknown, method: "GET" | "POST" = "POST"): Promise<T> {
  const response = await fetch(`${API_BASE}${path.startsWith("/") ? path : `/${path}`}`, {
    method,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof result.error === "string" ? result.error : typeof result.detail === "string" ? result.detail : `Request failed (${response.status})`);
  }
  return result as T;
}

export async function signIn(username: string, password: string): Promise<string> {
  const response = await fetch(`${API_BASE}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
    cache: "no-store",
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok || typeof result.access_token !== "string") {
    throw new Error(typeof result.error === "string" ? result.error : "Sign-in failed");
  }
  return result.access_token;
}
