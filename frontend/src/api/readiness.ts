import type { Locale } from "../i18n/locale";
import { apiUrl } from "./baseUrl";
import { withAppLocale } from "./pipelineHeaders";

export interface LibraryReadiness {
  book_count: number;
  enriched_count: number;
  needs_sync: boolean;
  needs_more_books: boolean;
  ready_for_recommendations: boolean;
}

export async function fetchLibraryReadiness(
  locale: Locale,
): Promise<LibraryReadiness> {
  const res = await fetch(
    apiUrl("/api/pipeline/readiness"),
    withAppLocale(locale, {}),
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<LibraryReadiness>;
}
