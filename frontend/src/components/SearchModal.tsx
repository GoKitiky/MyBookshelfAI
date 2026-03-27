import { useCallback, useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n/I18nContext";
import type { Book } from "../types";
import "./SearchModal.css";

interface Props {
  books: Book[];
  open: boolean;
  onClose: () => void;
  onSelect: (book: Book) => void;
}

export function SearchModal({ books, open, onClose, onSelect }: Props) {
  const { m, bookWord } = useI18n();
  const [query, setQuery] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const filtered = query.trim()
    ? books.filter((b) => {
        const q = query.toLowerCase();
        return (
          b.title.toLowerCase().includes(q) ||
          b.author.toLowerCase().includes(q)
        );
      })
    : books;

  useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIdx(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  useEffect(() => {
    setActiveIdx(0);
  }, [query]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIdx((i) => Math.min(i + 1, filtered.length - 1));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIdx((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === "Enter" && filtered[activeIdx]) {
        onSelect(filtered[activeIdx]);
        onClose();
      }
    },
    [filtered, activeIdx, onClose, onSelect],
  );

  useEffect(() => {
    const active = listRef.current?.querySelector(".search-result--active");
    active?.scrollIntoView({ block: "nearest" });
  }, [activeIdx]);

  if (!open) return null;

  return (
    <div className="search-overlay" onClick={onClose} role="presentation">
      <div
        className="search-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label={m.search.aria}
        onKeyDown={handleKeyDown}
      >
        <input
          ref={inputRef}
          className="search-input"
          type="text"
          placeholder={m.search.placeholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label={m.search.aria}
        />
        <div className="search-count" aria-live="polite">
          {m.search.found(filtered.length, bookWord(filtered.length))}
        </div>
        <ul className="search-results" ref={listRef} role="listbox">
          {filtered.map((b, i) => (
            <li
              key={b.id}
              role="option"
              aria-selected={i === activeIdx}
              className={`search-result ${i === activeIdx ? "search-result--active" : ""}`}
              onClick={() => {
                onSelect(b);
                onClose();
              }}
              onMouseEnter={() => setActiveIdx(i)}
            >
              <span className="search-result-title">{b.title}</span>
              <span className="search-result-author">{b.author}</span>
            </li>
          ))}
          {filtered.length === 0 && (
            <li className="search-empty">{m.search.noResults}</li>
          )}
        </ul>
      </div>
    </div>
  );
}
