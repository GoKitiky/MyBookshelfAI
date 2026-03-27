import { useCallback, useEffect, useRef, useState } from "react";
import { createBook } from "../api/books";
import { useI18n } from "../i18n/I18nContext";
import { useToast } from "./Toast";
import type { Book } from "../types";
import "./AddBookModal.css";

interface Props {
  open: boolean;
  onClose: () => void;
  onAdded: (book: Book) => void;
}

export function AddBookModal({ open, onClose, onAdded }: Props) {
  const { m } = useI18n();
  const { toast } = useToast();
  const titleRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [rating, setRating] = useState<string>("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setTitle("");
      setAuthor("");
      setRating("");
      setNotes("");
      requestAnimationFrame(() => titleRef.current?.focus());
    }
  }, [open]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const t = title.trim();
      const a = author.trim();
      if (!t || !a) {
        toast(m.library.addBookEmptyField);
        return;
      }
      const r = rating === "" ? null : Number(rating);
      setSaving(true);
      try {
        const book = await createBook({
          title: t,
          author: a,
          rating: r,
          notes_md: notes.trim(),
        });
        toast(m.library.addBookSuccess);
        onAdded(book);
        onClose();
      } catch (err) {
        toast(
          m.library.addBookFailed(
            err instanceof Error ? err.message : String(err),
          ),
        );
      } finally {
        setSaving(false);
      }
    },
    [title, author, rating, notes, toast, m, onAdded, onClose],
  );

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="add-book-overlay" onClick={onClose} role="presentation">
      <div
        className="add-book-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label={m.library.addBookDialogAria}
      >
        <h2 className="add-book-heading">{m.library.addBook}</h2>
        <form className="add-book-form" onSubmit={handleSubmit}>
          <label className="add-book-field">
            <span>{m.library.addBookTitleLabel}</span>
            <input
              ref={titleRef}
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              autoComplete="off"
              disabled={saving}
            />
          </label>
          <label className="add-book-field">
            <span>{m.library.addBookAuthorLabel}</span>
            <input
              type="text"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              autoComplete="off"
              disabled={saving}
            />
          </label>
          <label className="add-book-field">
            <span>{m.library.addBookRatingLabel}</span>
            <select
              value={rating}
              onChange={(e) => setRating(e.target.value)}
              disabled={saving}
            >
              <option value="">{m.library.addBookRatingNone}</option>
              <option value="1">1</option>
              <option value="2">2</option>
              <option value="3">3</option>
              <option value="4">4</option>
              <option value="5">5</option>
            </select>
          </label>
          <label className="add-book-field">
            <span>{m.library.addBookNotesLabel}</span>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={4}
              placeholder={m.library.addBookNotesPlaceholder}
              disabled={saving}
            />
          </label>
          <div className="add-book-actions">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={onClose}
              disabled={saving}
            >
              {m.bookPanel.cancel}
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? m.library.addBookSaving : m.library.addBookSubmit}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
