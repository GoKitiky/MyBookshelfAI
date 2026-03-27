export type Locale = "ru" | "en";

export const LOCALE_STORAGE_KEY = "mybookshelfai-locale";

/** Used only when a locale is required before first-run choice (SSR / tests). */
export const DEFAULT_LOCALE: Locale = "ru";

export function parseStoredLocale(raw: string | null): Locale | null {
  if (raw === "ru" || raw === "en") return raw;
  return null;
}
