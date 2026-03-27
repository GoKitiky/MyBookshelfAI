import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  fetchLibraryReadiness,
  type LibraryReadiness,
} from "../api/readiness";
import { fetchRecommendations } from "../api/recommend";
import { fetchReadingLists, toggleReadingList } from "../api/readingLists";
import { useI18n } from "../i18n/I18nContext";
import { recListKey } from "../lib/recListKey";
import { useToast } from "../components/Toast";
import { useLibraryPrepare } from "../hooks/useLibraryPrepare";
import { IndeterminateProgress } from "../components/IndeterminateProgress";
import {
  recBlockerFromMessage,
  shortRecErrorLabel,
} from "../lib/recBlocker";
import type { Recommendation } from "../types";
import "./RecommendationsPage.css";

const RECOMMENDATION_COUNT = 5;

export function RecommendationsPage() {
  const { m, locale } = useI18n();
  const { toast } = useToast();
  const [items, setItems] = useState<Recommendation[]>([]);
  const [fromCache, setFromCache] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [readiness, setReadiness] = useState<LibraryReadiness | null>(null);
  const [readinessLoading, setReadinessLoading] = useState(true);
  const [phraseIx, setPhraseIx] = useState(0);
  const phraseTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const { runPrepare, phase: preparePhase } = useLibraryPrepare(locale);
  const preparing = preparePhase !== "idle";
  const witty = m.rec.wittyPhrases;

  const [plannedKeys, setPlannedKeys] = useState(() => new Set<string>());
  const [blacklistKeys, setBlacklistKeys] = useState(() => new Set<string>());
  const [listActionBusy, setListActionBusy] = useState<string | null>(null);

  const clearPhraseTimer = () => {
    if (phraseTimer.current) {
      clearInterval(phraseTimer.current);
      phraseTimer.current = null;
    }
  };

  const runFetch = useCallback(
    async (refresh: boolean) => {
      setLoading(true);
      setError(null);
      setPhraseIx(0);
      clearPhraseTimer();
      phraseTimer.current = setInterval(() => {
        setPhraseIx((i) => (i + 1) % witty.length);
      }, 2200);
      try {
        const data = await fetchRecommendations(locale, refresh);
        setItems(data.recommendations);
        setFromCache(data.from_cache);
      } catch (e) {
        setItems([]);
        setFromCache(null);
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        clearPhraseTimer();
        setLoading(false);
      }
    },
    [witty, locale],
  );

  useEffect(() => {
    return () => clearPhraseTimer();
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setReadinessLoading(true);
      try {
        const r = await fetchLibraryReadiness(locale);
        if (cancelled) return;
        setReadiness(r);
        if (r.ready_for_recommendations) {
          await runFetch(false);
        }
      } catch {
        if (cancelled) return;
        setReadiness(null);
        await runFetch(false);
      } finally {
        if (!cancelled) setReadinessLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial mount only
  }, []);

  useEffect(() => {
    setPhraseIx((i) => (witty.length ? i % witty.length : 0));
  }, [locale, witty.length]);

  useEffect(() => {
    if (items.length === 0) return;
    let cancelled = false;
    fetchReadingLists()
      .then((data) => {
        if (cancelled) return;
        setPlannedKeys(
          new Set(data.planned.map((e) => recListKey(e.title, e.author))),
        );
        setBlacklistKeys(
          new Set(data.blacklist.map((e) => recListKey(e.title, e.author))),
        );
      })
      .catch(() => {
        if (cancelled) return;
        setPlannedKeys(new Set());
        setBlacklistKeys(new Set());
      });
    return () => {
      cancelled = true;
    };
  }, [items]);

  const applyListToggle = useCallback(
    (key: string, res: { planned: boolean; blacklist: boolean }) => {
      setPlannedKeys((prev) => {
        const n = new Set(prev);
        if (res.planned) n.add(key);
        else n.delete(key);
        return n;
      });
      setBlacklistKeys((prev) => {
        const n = new Set(prev);
        if (res.blacklist) n.add(key);
        else n.delete(key);
        return n;
      });
    },
    [],
  );

  const handleTogglePlanned = useCallback(
    async (rec: Recommendation) => {
      const key = recListKey(rec.title, rec.author);
      const busyId = `${key}:planned`;
      setListActionBusy(busyId);
      try {
        const res = await toggleReadingList({
          target: "planned",
          title: rec.title,
          author: rec.author,
          genres: rec.genres,
          reasoning: rec.reasoning,
        });
        applyListToggle(key, res);
      } catch (e) {
        const detail = e instanceof Error ? e.message : String(e);
        toast(m.rec.recListActionError(detail));
      } finally {
        setListActionBusy((b) => (b === busyId ? null : b));
      }
    },
    [applyListToggle, m.rec, toast],
  );

  const handleToggleBlacklist = useCallback(
    async (rec: Recommendation) => {
      const key = recListKey(rec.title, rec.author);
      const busyId = `${key}:blacklist`;
      setListActionBusy(busyId);
      try {
        const res = await toggleReadingList({
          target: "blacklist",
          title: rec.title,
          author: rec.author,
          genres: rec.genres,
          reasoning: rec.reasoning,
        });
        applyListToggle(key, res);
      } catch (e) {
        const detail = e instanceof Error ? e.message : String(e);
        toast(m.rec.recListActionError(detail));
      } finally {
        setListActionBusy((b) => (b === busyId ? null : b));
      }
    },
    [applyListToggle, m.rec, toast],
  );

  const refreshReadiness = useCallback(async () => {
    try {
      const r = await fetchLibraryReadiness(locale);
      setReadiness(r);
    } catch {
      setReadiness(null);
    }
  }, [locale]);

  const handlePrepare = async () => {
    setError(null);
    try {
      const data = await runPrepare(false);
      setItems(data.recommendations);
      setFromCache(data.from_cache);
      await refreshReadiness();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      await refreshReadiness();
    }
  };

  const ready = readiness?.ready_for_recommendations === true;
  const canFetch = ready || items.length > 0;
  const toolbarBusy = readinessLoading || loading || preparing;

  const blocked =
    !readinessLoading &&
    readiness &&
    !readiness.ready_for_recommendations &&
    !preparing &&
    !loading &&
    items.length === 0 &&
    !error;

  const prepareLabel =
    preparePhase === "enriching"
      ? m.rec.preparingEnrich
      : preparePhase === "loading_recs"
        ? m.rec.preparingRecs
        : witty[phraseIx] ?? "";

  const showLoadingShell =
    readinessLoading || loading || preparing;
  const loadingMessage = preparing
    ? prepareLabel
    : loading
      ? witty[phraseIx] ?? ""
      : m.rec.checkingLibrary;

  const errorBlocker = error ? recBlockerFromMessage(error) : null;

  return (
    <div className="rec-page">
      <div className="rec-header">
        <h1>{m.rec.title}</h1>
        <div className="rec-toolbar">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => void runFetch(false)}
            disabled={toolbarBusy || !canFetch}
          >
            {m.rec.load}
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void runFetch(true)}
            disabled={toolbarBusy || !canFetch}
          >
            {loading ? <span className="spinner" /> : null}
            {loading ? m.rec.wait : m.rec.refresh}
          </button>
        </div>
      </div>

      {blocked ? (
        <div className="rec-blocked">
          {readiness.needs_sync || readiness.book_count === 0 ? (
            <>
              <p className="rec-blocked-msg">{m.rec.blockedEmpty}</p>
              <Link className="btn btn-primary" to="/">
                {m.rec.syncLibrary}
              </Link>
            </>
          ) : null}
          {readiness.needs_more_books ? (
            <>
              <p className="rec-blocked-msg">{m.rec.blockedMoreBooks}</p>
              <Link className="btn btn-primary" to="/">
                {m.rec.openLibrary}
              </Link>
            </>
          ) : null}
          {!readiness.needs_sync &&
          !readiness.needs_more_books &&
          readiness.book_count >= 2 &&
          readiness.enriched_count === 0 ? (
            <>
              <p className="rec-blocked-msg">{m.rec.blockedEnrich}</p>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => void handlePrepare()}
                disabled={preparing}
              >
                {preparing ? <span className="spinner" /> : null}
                {preparing ? prepareLabel : m.rec.enrichCta}
              </button>
            </>
          ) : null}
        </div>
      ) : null}

      {error && !blocked ? (
        <div className="rec-error" role="alert">
          <p>
            {shortRecErrorLabel(
              error ? recBlockerFromMessage(error) : { kind: "other" },
              m.rec.errorShort,
            )}
          </p>
          <details className="rec-error-details">
            <summary>{m.rec.details}</summary>
            <pre className="rec-error-body">{error}</pre>
          </details>
          {errorBlocker?.kind === "need_enrich" ? (
            <button
              type="button"
              className="btn btn-primary rec-error-cta"
              onClick={() => void handlePrepare()}
              disabled={preparing}
            >
              {preparing ? <span className="spinner" /> : null}
              {preparing ? prepareLabel : m.rec.enrichCta}
            </button>
          ) : null}
          {errorBlocker?.kind === "need_sync" ||
          errorBlocker?.kind === "need_books" ? (
            <Link className="btn btn-primary rec-error-cta" to="/">
              {errorBlocker.kind === "need_sync"
                ? m.rec.syncLibrary
                : m.rec.openLibrary}
            </Link>
          ) : null}
        </div>
      ) : null}

      {showLoadingShell ? (
        <div className="rec-loading" aria-busy="true">
          <p className="rec-witty" aria-live="polite">
            {loadingMessage}
          </p>
          {preparing ? (
            <IndeterminateProgress statusText={prepareLabel} />
          ) : null}
          <ul className="rec-list" aria-hidden>
            {Array.from({ length: RECOMMENDATION_COUNT }, (_, i) => (
              <li key={i} className="rec-card rec-card--skeleton">
                <div className="rec-skeleton-head">
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="rec-skeleton-line rec-skeleton-line--title skeleton" />
                    <div className="rec-skeleton-line rec-skeleton-line--author skeleton" />
                  </div>
                  <div className="rec-skeleton-actions" aria-hidden>
                    <span className="rec-skeleton-action skeleton" />
                    <span className="rec-skeleton-action skeleton" />
                  </div>
                </div>
                <div className="rec-skeleton-genres">
                  <span className="rec-skeleton-chip skeleton" />
                  <span className="rec-skeleton-chip skeleton" />
                  <span className="rec-skeleton-chip rec-skeleton-chip--short skeleton" />
                </div>
                <div className="rec-skeleton-match">
                  <span className="rec-skeleton-match-label skeleton" />
                  <div className="rec-skeleton-match-track skeleton" />
                  <span className="rec-skeleton-match-pct skeleton" />
                </div>
                <div className="rec-skeleton-reason">
                  <div className="rec-skeleton-line rec-skeleton-line--body skeleton" />
                  <div className="rec-skeleton-line rec-skeleton-line--body skeleton" />
                  <div className="rec-skeleton-line rec-skeleton-line--body-short skeleton" />
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {!loading &&
      !preparing &&
      !readinessLoading &&
      !error &&
      items.length === 0 &&
      ready ? (
        <p className="rec-empty">{m.rec.empty}</p>
      ) : null}

      {!loading && !preparing && items.length > 0 ? (
        <ul className="rec-list" role="list">
          {items.map((rec, i) => {
            const rk = recListKey(rec.title, rec.author);
            const inPlanned = plannedKeys.has(rk);
            const inBlacklist = blacklistKeys.has(rk);
            const busy =
              listActionBusy === `${rk}:planned` ||
              listActionBusy === `${rk}:blacklist`;
            return (
            <li
              key={`${rec.title}-${rec.author}-${i}`}
              className="rec-card"
              style={{ "--stagger": i } as CSSProperties}
            >
              <div className="rec-card-head">
                <div className="rec-card-head-text">
                  <h2 className="rec-title">{rec.title}</h2>
                  <p className="rec-author">{rec.author}</p>
                </div>
                <div className="rec-card-actions">
                  <button
                    type="button"
                    className={
                      inPlanned
                        ? "rec-action rec-action--heart rec-action--active"
                        : "rec-action rec-action--heart"
                    }
                    aria-pressed={inPlanned}
                    aria-label={
                      inPlanned ? m.rec.removePlannedTitle : m.rec.savePlannedTitle
                    }
                    title={
                      inPlanned ? m.rec.removePlannedTitle : m.rec.savePlannedTitle
                    }
                    disabled={busy}
                    onClick={() => void handleTogglePlanned(rec)}
                  >
                    <HeartIcon filled={inPlanned} />
                  </button>
                  <button
                    type="button"
                    className={
                      inBlacklist
                        ? "rec-action rec-action--dismiss rec-action--active"
                        : "rec-action rec-action--dismiss"
                    }
                    aria-pressed={inBlacklist}
                    aria-label={
                      inBlacklist
                        ? m.rec.removeBlacklistTitle
                        : m.rec.saveBlacklistTitle
                    }
                    title={
                      inBlacklist
                        ? m.rec.removeBlacklistTitle
                        : m.rec.saveBlacklistTitle
                    }
                    disabled={busy}
                    onClick={() => void handleToggleBlacklist(rec)}
                  >
                    <BrokenHeartIcon />
                  </button>
                </div>
              </div>
              {rec.genres.length > 0 ? (
                <ul className="rec-genres">
                  {rec.genres.map((g) => (
                    <li key={g} className="rec-genre-chip">
                      {g}
                    </li>
                  ))}
                </ul>
              ) : null}
              <div
                className="rec-match"
                role="img"
                aria-label={m.rec.matchAria(
                  Math.round(clamp01(rec.match_score) * 100),
                )}
              >
                <span className="rec-match-label">{m.rec.match}</span>
                <div className="rec-match-track">
                  <div
                    className="rec-match-fill"
                    style={{
                      transform: `scaleX(${clamp01(rec.match_score)})`,
                    }}
                  />
                </div>
                <span className="rec-match-pct">
                  {Math.round(clamp01(rec.match_score) * 100)}%
                </span>
              </div>
              {rec.reasoning ? (
                <div className="rec-reason markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {rec.reasoning}
                  </ReactMarkdown>
                </div>
              ) : null}
            </li>
            );
          })}
        </ul>
      ) : null}

      {!loading && !preparing && items.length > 0 && fromCache !== null ? (
        <p className="rec-meta rec-meta--footer" aria-live="polite">
          {fromCache ? (
            <span className="rec-cache">{m.rec.fromCache}</span>
          ) : (
            <span className="rec-fresh">{m.rec.fresh}</span>
          )}
        </p>
      ) : null}
    </div>
  );
}

function clamp01(n: number): number {
  if (Number.isNaN(n)) return 0;
  return Math.min(1, Math.max(0, n));
}

function HeartIcon({ filled }: { filled: boolean }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      aria-hidden
      className="rec-action-icon"
    >
      {filled ? (
        <path
          fill="currentColor"
          d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
        />
      ) : (
        <path
          fill="none"
          stroke="currentColor"
          strokeWidth="1.85"
          strokeLinejoin="round"
          d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
        />
      )}
    </svg>
  );
}

/** Same heart silhouette as save-to-list, with a jagged crack (product UI parity). */
function BrokenHeartIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className="rec-action-icon"
    >
      <path
        stroke="currentColor"
        strokeWidth="1.85"
        strokeLinejoin="round"
        d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
      />
      <path
        stroke="currentColor"
        strokeWidth="1.85"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M10.85 5.65l2.35 3.35-1.95 2.35 2.05 2.95"
      />
    </svg>
  );
}
