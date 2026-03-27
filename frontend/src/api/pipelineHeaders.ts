import type { Locale } from "../i18n/locale";

const HEADER = "X-App-Locale";

/** Merge pipeline locale into fetch init (SPA sends fixed locale after first-run). */
export function withAppLocale(
  locale: Locale,
  init?: RequestInit,
): RequestInit {
  const headers = new Headers(init?.headers);
  headers.set(HEADER, locale);
  return { ...init, headers };
}
