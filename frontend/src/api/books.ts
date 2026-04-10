import type { Locale } from "../i18n/locale";
import type { Book, BooksResponse, LibraryListSort, SyncResult } from "../types";
import { apiUrl } from "./baseUrl";
import { withAppLocale } from "./pipelineHeaders";

const BASE = "/api/books";

/** Fired on `window` when library data should be refetched (e.g. after bulk demo clear). */
export const LIBRARY_UPDATED_EVENT = "mybookshelf:library-updated";

export function notifyLibraryUpdated(): void {
  window.dispatchEvent(new Event(LIBRARY_UPDATED_EVENT));
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(url), init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export type BookCreatePayload = {
  title: string;
  author: string;
  rating?: number | null;
  review?: string;
  tags?: string[];
  notes_md?: string;
};

export function createBook(payload: BookCreatePayload): Promise<Book> {
  return request<Book>(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: payload.title.trim(),
      author: payload.author.trim(),
      rating: payload.rating ?? null,
      review: payload.review ?? "",
      tags: payload.tags,
      notes_md: payload.notes_md ?? "",
    }),
  });
}

export function fetchBooks(
  locale: Locale,
  page: number,
  perPage: number,
  query = "",
  sort: LibraryListSort = "default",
): Promise<BooksResponse> {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
    sort,
  });
  if (query) params.set("q", query);
  return request<BooksResponse>(
    `${BASE}?${params}`,
    withAppLocale(locale, {}),
  );
}

export function fetchBook(id: string): Promise<Book> {
  return request<Book>(`${BASE}/${id}`);
}

export function updateBook(
  id: string,
  fields: Partial<
    Pick<Book, "title" | "author" | "rating" | "review" | "tags" | "notes_md">
  >,
): Promise<Book> {
  return request<Book>(`${BASE}/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
}

export function deleteBook(id: string): Promise<{ status: string }> {
  return request<{ status: string }>(`${BASE}/${id}`, { method: "DELETE" });
}

/** Demo clear uses a dedicated app route (see ``app.main.api_clear_demo_library``). */
export function clearDemoBooks(locale: Locale): Promise<{ removed: number }> {
  return request<{ removed: number }>(
    "/api/demo/clear-library",
    withAppLocale(locale, { method: "POST" }),
  );
}

export async function importBooks(files: FileList): Promise<SyncResult> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  const res = await fetch(apiUrl(`${BASE}/import`), { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<SyncResult>;
}
