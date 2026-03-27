import { useCallback, useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { importBooks } from "../api/books";
import { AddBookModal } from "../components/AddBookModal";
import { BookCard } from "../components/BookCard";
import { Pagination } from "../components/Pagination";
import { ReadingListModal } from "../components/ReadingListModal";
import { SearchModal } from "../components/SearchModal";
import { useToast } from "../components/Toast";
import { useI18n } from "../i18n/I18nContext";
import { useBooks } from "../hooks/useBooks";
import { useKeydown } from "../hooks/useKeyboard";
import type { Book, LibraryListSort } from "../types";
import "./LibraryPage.css";

/** Books fetched per page; tuned to ~7 columns × 4 rows at 1200px content width. */
const LIBRARY_PAGE_SIZE = 28;

const LIBRARY_SORT_VALUES: LibraryListSort[] = [
  "default",
  "title",
  "rating",
  "added",
];

export function LibraryPage() {
  const { m, bookWord, locale } = useI18n();
  const [listSort, setListSort] = useState<LibraryListSort>("default");
  const { books, total, page, totalPages, loading, error, setPage, refresh } =
    useBooks(locale, LIBRARY_PAGE_SIZE, listSort);
  const { toast } = useToast();

  const [searchOpen, setSearchOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);
  const [sortMenuOpen, setSortMenuOpen] = useState(false);
  const [plannedListOpen, setPlannedListOpen] = useState(false);
  const [blacklistOpen, setBlacklistOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const sortWrapRef = useRef<HTMLDivElement>(null);
  const sortMenuId = useId();

  const sortLabels: Record<LibraryListSort, string> = {
    default: m.library.sortDefault,
    title: m.library.sortTitle,
    rating: m.library.sortRating,
    added: m.library.sortAdded,
  };

  useEffect(() => {
    if (!sortMenuOpen) return;
    const onDocMouseDown = (e: MouseEvent) => {
      if (
        sortWrapRef.current &&
        !sortWrapRef.current.contains(e.target as Node)
      ) {
        setSortMenuOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSortMenuOpen(false);
    };
    document.addEventListener("mousedown", onDocMouseDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocMouseDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [sortMenuOpen]);

  const openSearch = useCallback(() => setSearchOpen(true), []);
  const closeSearch = useCallback(() => setSearchOpen(false), []);

  useKeydown(
    "o",
    (e) => {
      e.preventDefault();
      openSearch();
    },
    { ctrl: true },
  );

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setImporting(true);
    try {
      const result = await importBooks(files);
      toast(m.library.importSuccess(result.total, bookWord(result.total)));
      refresh();
    } catch (err) {
      toast(
        m.library.importFailed(
          err instanceof Error ? err.message : String(err),
        ),
      );
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleSelectBook = useCallback((book: Book) => {
    setSelectedBook(book);
  }, []);

  const handleClosePanel = useCallback(() => {
    setSelectedBook(null);
  }, []);

  const handleBookChanged = useCallback(
    (updated?: Book) => {
      refresh();
      if (updated) setSelectedBook(updated);
    },
    [refresh],
  );

  const handleBookAdded = useCallback(
    (book: Book) => {
      setPage(1);
      refresh();
      setSelectedBook(book);
    },
    [refresh, setPage],
  );

  return (
    <div className="library-page">
      <div className="library-header">
        <h1>{m.library.title}</h1>
        <div className="library-actions">
          <button
            type="button"
            className="btn btn-ghost library-lists-btn"
            onClick={() => setPlannedListOpen(true)}
            aria-label={m.library.plannedListOpenAria}
            title={m.library.plannedListShort}
          >
            <LibraryHeartIcon />
            <span className="library-lists-btn-text">{m.library.plannedListShort}</span>
          </button>
          <button
            type="button"
            className="btn btn-ghost library-lists-btn"
            onClick={() => setBlacklistOpen(true)}
            aria-label={m.library.blacklistListOpenAria}
            title={m.library.blacklistListShort}
          >
            <LibraryBrokenHeartIcon />
            <span className="library-lists-btn-text">{m.library.blacklistListShort}</span>
          </button>
          <button
            className="btn btn-ghost"
            onClick={openSearch}
            aria-label={m.search.aria}
            title={m.library.searchTitle}
          >
            <SearchIcon />
            {m.library.search}
          </button>
          <button
            type="button"
            className="btn btn-primary library-add-btn"
            onClick={() => setAddOpen(true)}
            aria-label={m.library.addBookAria}
            title={m.library.addBook}
          >
            <PlusIcon />
          </button>
          <button
            className="btn btn-primary"
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            aria-label={m.library.importAria}
          >
            {importing ? <span className="spinner" /> : <UploadIcon />}
            {importing ? m.library.importing : m.library.import_}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".md"
            hidden
            onChange={handleImport}
          />
        </div>
      </div>

      {error && <p className="library-error">{error}</p>}

      {loading && books.length === 0 ? (
        <div className="book-grid">
          {Array.from({ length: LIBRARY_PAGE_SIZE }, (_, i) => (
            <div key={i} className="skeleton-card skeleton" />
          ))}
        </div>
      ) : books.length === 0 ? (
        <div className="library-empty">
          <p>{m.library.empty}</p>
          <div className="library-empty-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setAddOpen(true)}
            >
              <PlusIcon />
              {m.library.addBook}
            </button>
            <button
              className="btn btn-ghost"
              onClick={() => fileInputRef.current?.click()}
            >
              <UploadIcon />
              {m.library.importMd}
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="library-toolbar">
            <div className="library-toolbar-row">
              <div className="library-sort" ref={sortWrapRef}>
                <button
                  type="button"
                  className="library-sort-trigger"
                  aria-label={`${m.library.sortAria}: ${sortLabels[listSort]}`}
                  aria-expanded={sortMenuOpen}
                  aria-haspopup="menu"
                  aria-controls={sortMenuId}
                  title={sortLabels[listSort]}
                  onClick={() => setSortMenuOpen((o) => !o)}
                >
                  <SortArrowsIcon />
                </button>
                {sortMenuOpen ? (
                  <div id={sortMenuId} className="library-sort-menu" role="menu">
                    {LIBRARY_SORT_VALUES.map((value) => (
                      <button
                        key={value}
                        type="button"
                        role="menuitemradio"
                        aria-checked={listSort === value}
                        className={
                          listSort === value
                            ? "library-sort-option library-sort-option-active"
                            : "library-sort-option"
                        }
                        onClick={() => {
                          setListSort(value);
                          setPage(1);
                          setSortMenuOpen(false);
                        }}
                      >
                        {sortLabels[value]}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
              <p className="library-count">
                {total} {bookWord(total)}
                {total >= 2 ? (
                  <>
                    {" "}
                    ·{" "}
                    <Link className="library-rec-link" to="/recommendations">
                      {m.library.getRecommendations}
                    </Link>
                  </>
                ) : null}
              </p>
            </div>
          </div>
          <div className="book-grid">
            {books.map((book) => (
              <BookCard
                key={book.id}
                book={book}
                onClick={() => handleSelectBook(book)}
              />
            ))}
          </div>
          <Pagination
            page={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </>
      )}

      <SearchModal
        books={books}
        open={searchOpen}
        onClose={closeSearch}
        onSelect={handleSelectBook}
      />

      <AddBookModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onAdded={handleBookAdded}
      />

      <ReadingListModal
        kind="planned"
        open={plannedListOpen}
        onClose={() => setPlannedListOpen(false)}
      />
      <ReadingListModal
        kind="blacklist"
        open={blacklistOpen}
        onClose={() => setBlacklistOpen(false)}
      />

      {selectedBook && (
        <BookPanel
          bookId={selectedBook.id}
          onClose={handleClosePanel}
          onChanged={handleBookChanged}
        />
      )}
    </div>
  );
}

/* Lazy-import to keep the panel code-split-friendly */
import { BookPanel } from "../components/BookPanel";

function SearchIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.25"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

/**
 * Solid twin arrows: up (left) and down (right), parallel — matches sort affordance.
 */
function SortArrowsIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      aria-hidden
    >
      <path
        fill="currentColor"
        d="M6 3 9.5 9H7.5v12H4.5V9H2.5L6 3z"
      />
      <path
        fill="currentColor"
        d="M18 21l-3.5-6h2V3h3v12h2l-3.5 6z"
      />
    </svg>
  );
}

function LibraryHeartIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      aria-hidden
      className="library-lists-icon"
    >
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.85"
        strokeLinejoin="round"
        d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
      />
    </svg>
  );
}

function LibraryBrokenHeartIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className="library-lists-icon"
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
