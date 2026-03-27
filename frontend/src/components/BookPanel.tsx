import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";
import { deleteBook, fetchBook, updateBook } from "../api/books";
import { useI18n } from "../i18n/I18nContext";
import { useToast } from "./Toast";
import type { Book } from "../types";
import "./BookPanel.css";

interface Props {
  bookId: string;
  onClose: () => void;
  /** Pass the saved book when the record may have a new id (title/author change). */
  onChanged: (book?: Book) => void;
}

function syncDraftsFromBook(b: Book) {
  return {
    notes: b.notes_md || b.review || "",
    title: b.title,
    author: b.author,
    rating: b.rating,
  };
}

export function BookPanel({ bookId, onClose, onChanged }: Props) {
  const [book, setBook] = useState<Book | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [draftTitle, setDraftTitle] = useState("");
  const [draftAuthor, setDraftAuthor] = useState("");
  const [draftRating, setDraftRating] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { toast } = useToast();
  const { m } = useI18n();
  const mRef = useRef(m);
  mRef.current = m;
  const panelRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const triggerRef = useRef<Element | null>(null);

  useEffect(() => {
    triggerRef.current = document.activeElement;
    return () => {
      if (triggerRef.current instanceof HTMLElement) {
        triggerRef.current.focus();
      }
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchBook(bookId)
      .then((b) => {
        if (!cancelled) {
          setBook(b);
          const d = syncDraftsFromBook(b);
          setDraft(d.notes);
          setDraftTitle(d.title);
          setDraftAuthor(d.author);
          setDraftRating(d.rating);
        }
      })
      .catch(() => {
        if (!cancelled) toast(mRef.current.bookPanel.loadFailed);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [bookId, toast]);

  const handleSave = useCallback(async () => {
    if (!book) return;
    const t = draftTitle.trim();
    const a = draftAuthor.trim();
    if (!t || !a) {
      toast(mRef.current.library.addBookEmptyField);
      return;
    }
    setSaving(true);
    try {
      const updated = await updateBook(book.id, {
        title: t,
        author: a,
        rating: draftRating,
        notes_md: draft,
      });
      setBook(updated);
      const d = syncDraftsFromBook(updated);
      setDraft(d.notes);
      setDraftTitle(d.title);
      setDraftAuthor(d.author);
      setDraftRating(d.rating);
      setEditing(false);
      toast(mRef.current.bookPanel.saved);
      onChanged(updated);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.startsWith("409:")) {
        toast(mRef.current.bookPanel.saveConflict);
      } else {
        toast(mRef.current.bookPanel.saveFailed);
      }
    } finally {
      setSaving(false);
    }
  }, [
    book,
    draft,
    draftAuthor,
    draftRating,
    draftTitle,
    onChanged,
    toast,
  ]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        if (confirmDelete) {
          setConfirmDelete(false);
        } else {
          onClose();
        }
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "s" && editing) {
        e.preventDefault();
        handleSave();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [confirmDelete, editing, handleSave, onClose]);

  useEffect(() => {
    if (editing && textareaRef.current) {
      textareaRef.current.focus();
      autoResize(textareaRef.current);
    }
  }, [editing]);

  const isNotesDirty =
    book != null && draft !== (book.notes_md ?? "");
  const isMetaDirty =
    book != null &&
    (draftTitle.trim() !== book.title ||
      draftAuthor.trim() !== book.author ||
      draftRating !== book.rating);

  useEffect(() => {
    if (!editing) return;
    const handler = (e: BeforeUnloadEvent) => {
      if (isNotesDirty || isMetaDirty) {
        e.preventDefault();
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [editing, isMetaDirty, isNotesDirty]);

  const handleDelete = useCallback(async () => {
    if (!book) return;
    try {
      await deleteBook(book.id);
      toast(mRef.current.bookPanel.deleted);
      onChanged();
      onClose();
    } catch {
      toast(mRef.current.bookPanel.deleteFailed);
    }
  }, [book, toast, onChanged, onClose]);

  function autoResize(el: HTMLTextAreaElement) {
    el.style.height = "auto";
    el.style.height = el.scrollHeight + "px";
  }

  function resetDraftsFromBook(b: Book) {
    const d = syncDraftsFromBook(b);
    setDraft(d.notes);
    setDraftTitle(d.title);
    setDraftAuthor(d.author);
    setDraftRating(d.rating);
  }

  function toggleEditing() {
    if (!book) return;
    if (editing) {
      resetDraftsFromBook(book);
    }
    setEditing(!editing);
  }

  return (
    <>
      <div
        className="panel-overlay"
        onClick={onClose}
        role="presentation"
      />
      <aside
        ref={panelRef}
        className="book-panel"
        role="dialog"
        aria-label={
          book
            ? m.bookPanel.dialogAria(editing ? draftTitle.trim() || book.title : book.title)
            : m.bookPanel.dialogFallbackAria
        }
      >
        <div className="panel-header">
          <button
            className="btn btn-ghost panel-close"
            onClick={onClose}
            aria-label={m.bookPanel.closeAria}
          >
            ✕
          </button>
        </div>

        {loading ? (
          <div className="panel-body">
            <div className="skeleton" style={{ height: 24, width: "70%" }} />
            <div
              className="skeleton"
              style={{ height: 16, width: "40%", marginTop: 8 }}
            />
            <div
              className="skeleton"
              style={{ height: 120, width: "100%", marginTop: 24 }}
            />
          </div>
        ) : book ? (
          <div className="panel-body">
            {editing ? (
              <>
                <label className="panel-field">
                  <span>{m.bookPanel.fieldTitle}</span>
                  <input
                    className="panel-input"
                    value={draftTitle}
                    onChange={(e) => setDraftTitle(e.target.value)}
                    autoComplete="off"
                  />
                </label>
                <label className="panel-field">
                  <span>{m.bookPanel.fieldAuthor}</span>
                  <input
                    className="panel-input"
                    value={draftAuthor}
                    onChange={(e) => setDraftAuthor(e.target.value)}
                    autoComplete="off"
                  />
                </label>
                <div
                  className="panel-field panel-field--rating"
                  role="group"
                  aria-label={m.bookPanel.ratingLabel}
                >
                  <span>{m.bookPanel.ratingLabel}</span>
                  <div className="panel-rating-edit">
                    {Array.from({ length: 5 }, (_, i) => {
                      const n = i + 1;
                      const filled = draftRating != null && n <= draftRating;
                      return (
                        <button
                          key={n}
                          type="button"
                          className={
                            filled ? "panel-star panel-star--filled" : "panel-star panel-star--empty"
                          }
                          aria-pressed={filled}
                          aria-label={m.bookPanel.ratingValueAria(n)}
                          onClick={() => setDraftRating(n)}
                        >
                          ★
                        </button>
                      );
                    })}
                    <button
                      type="button"
                      className="btn btn-ghost panel-clear-rating"
                      onClick={() => setDraftRating(null)}
                    >
                      {m.bookPanel.clearRating}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <>
                <h2 className="panel-title">{book.title}</h2>
                <p className="panel-author">{book.author}</p>

                {book.rating != null && (
                  <div className="panel-rating">
                    {Array.from({ length: 5 }, (_, i) => (
                      <span
                        key={i}
                        className={i < book.rating! ? "star--filled" : "star--empty"}
                      >
                        ★
                      </span>
                    ))}
                  </div>
                )}
              </>
            )}

            {book.tags.length > 0 && (
              <div className="panel-tags">
                {book.tags.map((tag) => (
                  <span key={tag} className="tag-pill">
                    {tag}
                  </span>
                ))}
              </div>
            )}

            <div className="panel-divider" />

            <div className="panel-notes-header">
              <span className="panel-notes-label">{m.bookPanel.notes}</span>
            </div>

            {editing ? (
              <div className="panel-editor">
                <textarea
                  ref={textareaRef}
                  className="panel-textarea"
                  value={draft}
                  onChange={(e) => {
                    setDraft(e.target.value);
                    autoResize(e.target);
                  }}
                />
                <button
                  className="btn btn-primary"
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? (
                    <>
                      <span className="spinner" /> {m.bookPanel.saving}
                    </>
                  ) : (
                    m.bookPanel.save
                  )}
                </button>
              </div>
            ) : (
              <div className="panel-markdown">
                {(book.notes_md || book.review) ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                    {book.notes_md || book.review}
                  </ReactMarkdown>
                ) : (
                  <p className="panel-empty-notes">{m.bookPanel.emptyNotes}</p>
                )}
              </div>
            )}

            <div className="panel-divider" />

            <div className="panel-footer-actions">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={toggleEditing}
              >
                {editing ? m.bookPanel.cancel : m.bookPanel.edit}
              </button>
              {confirmDelete ? (
                <div className="panel-confirm-delete">
                  <p>{m.bookPanel.confirmDelete}</p>
                  <div className="panel-confirm-actions">
                    <button
                      className="btn btn-ghost"
                      onClick={() => setConfirmDelete(false)}
                      autoFocus
                    >
                      {m.bookPanel.cancel}
                    </button>
                    <button className="btn btn-danger" onClick={handleDelete}>
                      {m.bookPanel.delete}
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={() => setConfirmDelete(true)}
                >
                  {m.bookPanel.deleteBook}
                </button>
              )}
            </div>
          </div>
        ) : null}
      </aside>
    </>
  );
}
