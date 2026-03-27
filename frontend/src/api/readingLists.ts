import type { ReadingListsResponse, ReadingListToggleResult } from "../types";

const BASE = "/api/reading-lists";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export function fetchReadingLists(): Promise<ReadingListsResponse> {
  return request<ReadingListsResponse>(BASE);
}

export function toggleReadingList(payload: {
  target: "planned" | "blacklist";
  title: string;
  author: string;
  genres?: string[];
  reasoning?: string;
}): Promise<ReadingListToggleResult> {
  return request<ReadingListToggleResult>(`${BASE}/toggle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: payload.target,
      title: payload.title.trim(),
      author: payload.author.trim(),
      genres: payload.genres ?? [],
      reasoning: payload.reasoning ?? "",
    }),
  });
}

export function removePlannedEntry(id: string): Promise<void> {
  return request<void>(`${BASE}/planned/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export function removeBlacklistEntry(id: string): Promise<void> {
  return request<void>(`${BASE}/blacklist/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}
