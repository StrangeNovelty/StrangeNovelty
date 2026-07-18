export type Json = Record<string, unknown>;
function csrf(): string {
  return (
    document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')
      ?.content ?? ""
  );
}
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const mutation = !["GET", "HEAD", "OPTIONS"].includes(init.method ?? "GET");
  const response = await fetch(`/api/story-engine-next${path}`, {
    credentials: "same-origin",
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(mutation ? { "X-CSRFToken": csrf() } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ error: "The request failed." }));
    throw new Error(
      String(body.error ?? `Request failed (${response.status})`),
    );
  }
  return response.json() as Promise<T>;
}
export const post = <T>(path: string, data: Json = {}) =>
  api<T>(path, { method: "POST", body: JSON.stringify(data) });
export const patch = <T>(path: string, data: Json) =>
  api<T>(path, { method: "PATCH", body: JSON.stringify(data) });
export const remove = <T>(path: string) =>
  api<T>(path, { method: "DELETE", headers: { "X-CSRFToken": csrf() } });
