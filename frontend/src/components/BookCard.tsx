import { useI18n } from "../i18n/I18nContext";
import type { Book } from "../types";
import "./BookCard.css";

interface Props {
  book: Book;
  onClick: () => void;
}

export function BookCard({ book, onClick }: Props) {
  const { m } = useI18n();

  return (
    <button
      className="book-card"
      onClick={onClick}
      aria-label={m.bookCard.openAria(book.title, book.author)}
    >
      <h3 className="book-card-title">{book.title}</h3>
      <p className="book-card-author">{book.author}</p>
      {book.rating != null && (
        <div
          className="book-card-rating"
          aria-label={m.bookCard.ratingAria(book.rating)}
        >
          {Array.from({ length: 5 }, (_, i) => (
            <span
              key={i}
              className={`star ${i < book.rating! ? "star--filled" : "star--empty"}`}
            >
              ★
            </span>
          ))}
        </div>
      )}
      {book.tags.length > 0 && (
        <div className="book-card-tags">
          {book.tags.slice(0, 4).map((tag) => (
            <span key={tag} className="tag-pill">
              {tag}
            </span>
          ))}
          {book.tags.length > 4 && (
            <span className="tag-pill tag-pill--more">
              +{book.tags.length - 4}
            </span>
          )}
        </div>
      )}
    </button>
  );
}
