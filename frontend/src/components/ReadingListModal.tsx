import { useCallback, useEffect, useState } from "react";
import {
  fetchReadingLists,
  removeBlacklistEntry,
  removePlannedEntry,
} from "../api/readingLists";
import { useI18n } from "../i18n/I18nContext";
import { useToast } from "./Toast";
import type { ReadingListEntry } from "../types";
import "./ReadingListModal.css";

type ListKind = "planned" | "blacklist";

interface Props {
  kind: ListKind;
  open: boolean;
  onClose: () => void;
}

export function ReadingListModal({ kind, open, onClose }: Props) {
  const { m } = useI18n();
  const { toast } = useToast();
  const [entries, setEntries] = useState<ReadingListEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const title =
    kind === "planned" ? m.library.plannedListTitle : m.library.blacklistTitle;

  const load = useCallback(() => {
    setLoading(true);
    fetchReadingLists()
      .then((data) => {
        setEntries(kind === "planned" ? data.planned : data.blacklist);
      })
      .catch((err: unknown) => {
        const detail = err instanceof Error ? err.message : String(err);
        toast(m.library.readingListLoadError(detail));
      })
      .finally(() => setLoading(false));
  }, [kind, m.library.readingListLoadError, toast]);

  useEffect(() => {
    if (!open) return;
    load();
  }, [open, load]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const handleRemove = async (entry: ReadingListEntry) => {
    try {
      if (kind === "planned") {
        await removePlannedEntry(entry.id);
      } else {
        await removeBlacklistEntry(entry.id);
      }
      setEntries((prev) => prev.filter((e) => e.id !== entry.id));
    } catch (err: unknown) {
      const detail = err instanceof Error ? err.message : String(err);
      toast(m.library.readingListLoadError(detail));
    }
  };

  if (!open) return null;

  const aria =
    kind === "planned"
      ? m.library.plannedListDialogAria
      : m.library.blacklistListDialogAria;

  return (
    <div className="reading-list-overlay" onClick={onClose} role="presentation">
      <div
        className="reading-list-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label={aria}
      >
        <div className="reading-list-modal-head">
          <h2 className="reading-list-modal-title">{title}</h2>
          <button
            type="button"
            className="reading-list-modal-close"
            onClick={onClose}
            aria-label={m.bookPanel.closeAria}
          >
            ×
          </button>
        </div>
        {loading ? (
          <p className="reading-list-modal-status">{m.library.readingListLoading}</p>
        ) : entries.length === 0 ? (
          <p className="reading-list-modal-empty">{m.library.readingListEmpty}</p>
        ) : (
          <ul className="reading-list-modal-list" role="list">
            {entries.map((e) => (
              <li key={e.id} className="reading-list-modal-row">
                <div className="reading-list-modal-text">
                  <span className="reading-list-modal-book-title">{e.title}</span>
                  <span className="reading-list-modal-book-author">{e.author}</span>
                </div>
                <button
                  type="button"
                  className="reading-list-modal-remove"
                  onClick={() => void handleRemove(e)}
                  aria-label={m.library.removeFromListAria(e.title)}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
