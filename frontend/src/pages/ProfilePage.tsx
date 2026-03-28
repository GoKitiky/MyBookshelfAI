import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { fetchLibraryReadiness } from "../api/readiness";
import { buildProfile, fetchProfile } from "../api/recommend";
import { IndeterminateProgress } from "../components/IndeterminateProgress";
import { useToast } from "../components/Toast";
import { useI18n } from "../i18n/I18nContext";
import { useLibraryPrepare } from "../hooks/useLibraryPrepare";
import type { ReaderProfile, WeightedTag } from "../types";
import "./ProfilePage.css";

const PROFILE_VIZ_TOP_N = 5;

function topNWeightedTags(tags: WeightedTag[], n: number): WeightedTag[] {
  const cleaned = tags
    .map((t) => ({
      name: String(t.name ?? "").trim(),
      weight: Math.max(0, Number(t.weight) || 0),
    }))
    .filter((t) => t.name.length > 0);
  cleaned.sort((a, b) => b.weight - a.weight);
  return cleaned.slice(0, n);
}

function topNAuthors(names: string[], n: number): string[] {
  return names.map((a) => a.trim()).filter(Boolean).slice(0, n);
}

function topNMoods(moods: string[], n: number): string[] {
  const u = moods.map((m) => m.trim()).filter(Boolean);
  return u.slice(0, n);
}

/** True when GET /profile failed because the library has no books (readiness may be unavailable). */
function isEmptyLibraryProfileError(msg: string): boolean {
  if (!msg.startsWith("400")) return false;
  const lower = msg.toLowerCase();
  return (
    lower.includes("no books in library") ||
    lower.includes("library is empty") ||
    lower.includes("import .md files first")
  );
}

export function ProfilePage() {
  const { toast } = useToast();
  const { m, locale } = useI18n();
  const mRef = useRef(m);
  mRef.current = m;
  const [profile, setProfile] = useState<ReaderProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [building, setBuilding] = useState(false);
  const [missing, setMissing] = useState(false);
  const [noBooks, setNoBooks] = useState(false);
  const { runPrepare, preparing, phase } = useLibraryPrepare(locale);

  const load = useCallback(async () => {
    setLoading(true);
    setMissing(false);
    setNoBooks(false);
    try {
      try {
        const readiness = await fetchLibraryReadiness(locale);
        if (readiness.book_count === 0) {
          setProfile(null);
          setNoBooks(true);
          return;
        }
      } catch {
        // If readiness fails, still try loading the profile.
      }
      const p = await fetchProfile(locale);
      setProfile(p);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      if (isEmptyLibraryProfileError(msg)) {
        setProfile(null);
        setNoBooks(true);
      } else if (msg.startsWith("404")) {
        setProfile(null);
        setMissing(true);
      } else {
        toast(mRef.current.profile.loadFailed(msg));
        setProfile(null);
      }
    } finally {
      setLoading(false);
    }
  }, [toast, locale]);

  useEffect(() => {
    void load();
  }, [load]);

  const handlePrepare = async () => {
    try {
      await runPrepare(false);
      await load();
      toast(m.profile.ready);
    } catch (e) {
      toast(
        m.profile.prepareFailed(
          e instanceof Error ? e.message : String(e),
        ),
      );
    }
  };

  const handleRebuild = async () => {
    setBuilding(true);
    try {
      const p = await buildProfile(locale, true);
      setProfile(p);
      setMissing(false);
      setNoBooks(false);
      toast(m.profile.rebuilt);
    } catch (e) {
      toast(
        m.profile.rebuildFailed(
          e instanceof Error ? e.message : String(e),
        ),
      );
    } finally {
      setBuilding(false);
    }
  };

  const prepareBusyLabel =
    phase === "enriching"
      ? m.profile.preparingEnrich
      : m.profile.preparingRecs;

  const topGenres = useMemo(
    () => (profile ? topNWeightedTags(profile.top_genres, PROFILE_VIZ_TOP_N) : []),
    [profile],
  );
  const topThemes = useMemo(
    () => (profile ? topNWeightedTags(profile.top_themes, PROFILE_VIZ_TOP_N) : []),
    [profile],
  );
  const topAuthors = useMemo(
    () => (profile ? topNAuthors(profile.favorite_authors, PROFILE_VIZ_TOP_N) : []),
    [profile],
  );
  const topMoods = useMemo(
    () =>
      profile ? topNMoods(profile.preferred_moods, PROFILE_VIZ_TOP_N) : [],
    [profile],
  );

  return (
    <div className="profile-page">
      <div className="profile-header">
        <h1>{m.profile.title}</h1>
        <div className="profile-actions">
          {profile ? (
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => void handleRebuild()}
              disabled={building || preparing}
            >
              {building ? <span className="spinner" /> : null}
              {building ? m.profile.rebuilding : m.profile.rebuild}
            </button>
          ) : null}
        </div>
      </div>

      {loading && !profile ? (
        <div className="profile-skeletons">
          <div className="skeleton profile-skel-block skeleton" />
          <div className="skeleton profile-skel-bars skeleton" />
          <div className="skeleton profile-skel-bars skeleton" />
        </div>
      ) : null}

      {noBooks && !loading ? (
        <div className="profile-empty">
          <p className="profile-empty-title">{m.profile.emptyLibraryTitle}</p>
          <p className="profile-empty-sub">{m.profile.emptyLibraryHint}</p>
          <Link className="btn btn-primary" to="/">
            {m.profile.emptyLibraryCta}
          </Link>
        </div>
      ) : null}

      {missing && !loading && !noBooks ? (
        <div className="profile-empty">
          <p className="profile-empty-title">{m.profile.emptyTitle}</p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void handlePrepare()}
            disabled={preparing}
          >
            {preparing ? <span className="spinner" /> : null}
            {preparing ? prepareBusyLabel : m.profile.prepareCta}
          </button>
          {preparing ? (
            <div className="profile-prepare-progress">
              <IndeterminateProgress statusText={prepareBusyLabel} />
            </div>
          ) : null}
          <p className="profile-empty-sub">
            {m.profile.emptySubBefore}{" "}
            <Link to="/">{m.profile.emptySubLink}</Link>{" "}
            {m.profile.emptySubAfter}
          </p>
        </div>
      ) : null}

      {profile ? (
        <div className="profile-body">
          <section className="profile-section" aria-labelledby="summary-heading">
            <h2 id="summary-heading">{m.profile.summary}</h2>
            <div className="profile-summary markdown-body">
              {profile.summary ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {profile.summary}
                </ReactMarkdown>
              ) : (
                <p className="profile-muted">{m.profile.noSummary}</p>
              )}
            </div>
          </section>

          <div className="profile-dashboard">
            <div className="profile-charts-row" role="presentation">
              <section
                className="profile-section profile-section--chart profile-chart-panel"
                aria-labelledby="genres-heading"
              >
                <h2 id="genres-heading">{m.profile.topGenres}</h2>
                <WeightedTagDonut
                  tags={topGenres}
                  chartLabel={m.profile.topGenres}
                />
              </section>
              <section
                className="profile-section profile-section--chart profile-chart-panel"
                aria-labelledby="themes-heading"
              >
                <h2 id="themes-heading">{m.profile.topThemes}</h2>
                <WeightedTagDonut
                  tags={topThemes}
                  chartLabel={m.profile.topThemes}
                />
              </section>
            </div>

            <div className="profile-bottom-row" role="presentation">
              <section
                className="profile-section profile-bottom-panel"
                aria-labelledby="moods-heading"
              >
                <h2 id="moods-heading">{m.profile.moods}</h2>
                <ul className="profile-chip-list profile-chip-list--spread">
                  {(topMoods.length ? topMoods : ["—"]).map((mood) => (
                    <li key={mood} className="profile-chip">
                      {mood}
                    </li>
                  ))}
                </ul>
              </section>
              <section
                className="profile-section profile-bottom-panel"
                aria-labelledby="authors-heading"
              >
                <h2 id="authors-heading">{m.profile.favoriteAuthors}</h2>
                <AuthorTopList authors={topAuthors} />
              </section>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

const DONUT_VIEW = 100;
const DONUT_CX = 50;
const DONUT_CY = 50;
const DONUT_R_OUT = 38;
const DONUT_R_IN = 22;

const DONUT_COLOR_CLASS = [
  "profile-donut-seg--0",
  "profile-donut-seg--1",
  "profile-donut-seg--2",
  "profile-donut-seg--3",
  "profile-donut-seg--4",
  "profile-donut-seg--5",
  "profile-donut-seg--6",
  "profile-donut-seg--7",
] as const;

function donutSlicePath(
  cx: number,
  cy: number,
  rOuter: number,
  rInner: number,
  a0: number,
  a1: number,
): string {
  if (a1 - a0 >= 2 * Math.PI - 1e-6) {
    const p1 = donutSlicePath(cx, cy, rOuter, rInner, a0, a0 + Math.PI);
    const p2 = donutSlicePath(
      cx,
      cy,
      rOuter,
      rInner,
      a0 + Math.PI,
      a0 + 2 * Math.PI,
    );
    return `${p1} ${p2}`;
  }
  const large = a1 - a0 > Math.PI ? 1 : 0;
  const xo0 = cx + rOuter * Math.cos(a0);
  const yo0 = cy + rOuter * Math.sin(a0);
  const xo1 = cx + rOuter * Math.cos(a1);
  const yo1 = cy + rOuter * Math.sin(a1);
  const xi1 = cx + rInner * Math.cos(a1);
  const yi1 = cy + rInner * Math.sin(a1);
  const xi0 = cx + rInner * Math.cos(a0);
  const yi0 = cy + rInner * Math.sin(a0);
  return [
    `M ${xo0} ${yo0}`,
    `A ${rOuter} ${rOuter} 0 ${large} 1 ${xo1} ${yo1}`,
    `L ${xi1} ${yi1}`,
    `A ${rInner} ${rInner} 0 ${large} 0 ${xi0} ${yi0}`,
    "Z",
  ].join(" ");
}

function segmentsFromFractions(fracs: number[]): { a0: number; a1: number }[] {
  const start = -Math.PI / 2;
  let acc = start;
  return fracs.map((f) => {
    const a0 = acc;
    const a1 = acc + f * 2 * Math.PI;
    acc = a1;
    return { a0, a1 };
  });
}

function WeightedTagDonut({
  tags,
  chartLabel,
}: {
  tags: WeightedTag[];
  chartLabel: string;
}) {
  const { m } = useI18n();
  const ariaSegment = m.profile.tagBarAria;

  const normalized = useMemo(() => {
    const withW = tags
      .map((t) => ({ name: t.name.trim(), weight: Math.max(0, t.weight) }))
      .filter((t) => t.name.length > 0);
    const sum = withW.reduce((s, t) => s + t.weight, 0);
    if (sum <= 0) return [];
    return withW.map((t) => ({
      name: t.name,
      weight: t.weight,
      frac: t.weight / sum,
      pct: Math.round((t.weight / sum) * 100),
    }));
  }, [tags]);

  if (!normalized.length) {
    return <p className="profile-muted">{m.profile.noData}</p>;
  }

  const fracs = normalized.map((n) => n.frac);
  const arcs = segmentsFromFractions(fracs);
  const summaryLabel = `${chartLabel}: ${normalized
    .map((n) => ariaSegment(n.name, n.pct))
    .join("; ")}`;

  return (
    <div className="profile-donut-block">
      <svg
        className="profile-donut-svg"
        viewBox={`0 0 ${DONUT_VIEW} ${DONUT_VIEW}`}
        role="img"
        aria-label={summaryLabel}
      >
        <title>{summaryLabel}</title>
        {normalized.map((n, i) => {
          const arc = arcs[i];
          if (!arc) return null;
          return (
            <path
              key={n.name}
              className={`profile-donut-seg ${DONUT_COLOR_CLASS[i % DONUT_COLOR_CLASS.length]}`}
              d={donutSlicePath(
                DONUT_CX,
                DONUT_CY,
                DONUT_R_OUT,
                DONUT_R_IN,
                arc.a0,
                arc.a1,
              )}
            />
          );
        })}
      </svg>
      <ul className="profile-donut-legend" aria-hidden="true">
        {normalized.map((n, i) => (
          <li key={n.name} className="profile-donut-legend-item">
            <span
              className={`profile-donut-swatch ${DONUT_COLOR_CLASS[i % DONUT_COLOR_CLASS.length]}`}
              aria-hidden
            />
            <span className="profile-donut-legend-text">
              <span className="profile-donut-legend-name">{n.name}</span>
              <span className="profile-donut-legend-pct">{n.pct}%</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function AuthorTopList({ authors }: { authors: string[] }) {
  const { m } = useI18n();

  if (!authors.length) {
    return <p className="profile-muted">{m.profile.noData}</p>;
  }

  return (
    <ol className="profile-authors-list">
      {authors.map((name, i) => (
        <li key={`${i}-${name}`} className="profile-authors-list-item">
          <span className="profile-authors-rank">{i + 1}</span>
          <span className="profile-authors-name">{name}</span>
        </li>
      ))}
    </ol>
  );
}
