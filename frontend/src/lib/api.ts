const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:5000/api/v1";

export type RoutingResult = {
  route: string;
  priority: string;
  reasons: string[];
  diagnosis: null;
  decision_support_only: true;
  requires_clinician_review: true;
  biomechanics?: {
    landmark_count: number;
    normalized_path_length: number;
    interpretation: string;
  };
};

export async function apiRequest<T>(
  path: string,
  token: string,
  body?: unknown,
  method: "GET" | "POST" = "POST"
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body === undefined ? {} : { "Content-Type": "application/json" })
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store"
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof result.error === "string" ? result.error : `Request failed (${response.status})`);
  }
  return result as T;
}

export async function signIn(username: string, password: string): Promise<string> {
  const response = await fetch(`${API_BASE}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
    cache: "no-store"
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok || typeof result.access_token !== "string") {
    throw new Error(typeof result.error === "string" ? result.error : "Sign-in failed");
  }
  return result.access_token;
}
