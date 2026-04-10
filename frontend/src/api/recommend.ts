import type { Locale } from "../i18n/locale";
import type {
  EnrichResponse,
  ReaderProfile,
  RecommendationsResponse,
} from "../types";
import { apiUrl } from "./baseUrl";
import { withAppLocale } from "./pipelineHeaders";

const PIPELINE = "/api/pipeline";

async function request<T>(
  locale: Locale,
  url: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(apiUrl(url), withAppLocale(locale, init));
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export function enrichBooks(
  locale: Locale,
  force = false,
): Promise<EnrichResponse> {
  const q = force ? "?force=true" : "";
  return request<EnrichResponse>(locale, `${PIPELINE}/books/enrich${q}`, {
    method: "POST",
  });
}

export function fetchProfile(locale: Locale): Promise<ReaderProfile> {
  return request<ReaderProfile>(locale, `${PIPELINE}/profile`);
}

export function buildProfile(
  locale: Locale,
  force = false,
): Promise<ReaderProfile> {
  const q = force ? "?force=true" : "";
  return request<ReaderProfile>(locale, `${PIPELINE}/profile/build${q}`, {
    method: "POST",
  });
}

export function fetchRecommendations(
  locale: Locale,
  refresh = false,
): Promise<RecommendationsResponse> {
  const params = new URLSearchParams({
    refresh: refresh ? "true" : "false",
  });
  return request<RecommendationsResponse>(
    locale,
    `${PIPELINE}/recommendations?${params}`,
    { method: "POST" },
  );
}
