import { useCallback, useState } from "react";
import { enrichBooks, fetchRecommendations } from "../api/recommend";
import type { Locale } from "../i18n/locale";
import type { RecommendationsResponse } from "../types";

export type PreparePhase = "idle" | "enriching" | "loading_recs";

export function useLibraryPrepare(locale: Locale) {
  const [phase, setPhase] = useState<PreparePhase>("idle");

  const runPrepare = useCallback(
    async (refreshRecs: boolean): Promise<RecommendationsResponse> => {
      setPhase("enriching");
      try {
        await enrichBooks(locale, false);
      } catch (e) {
        setPhase("idle");
        throw e;
      }
      setPhase("loading_recs");
      try {
        const data = await fetchRecommendations(locale, refreshRecs);
        setPhase("idle");
        return data;
      } catch (e) {
        setPhase("idle");
        throw e;
      }
    },
    [locale],
  );

  return {
    runPrepare,
    phase,
    preparing: phase !== "idle",
  };
}
