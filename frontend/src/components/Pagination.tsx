import { useI18n } from "../i18n/I18nContext";
import "./Pagination.css";

interface Props {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, totalPages, onPageChange }: Props) {
  const { m } = useI18n();

  if (totalPages <= 1) return null;

  return (
    <nav className="pagination" aria-label={m.pagination.aria}>
      <button
        className="btn btn-ghost pagination-btn"
        disabled={page <= 1}
        onClick={() => {
          onPageChange(page - 1);
          window.scrollTo({ top: 0, behavior: "smooth" });
        }}
      >
        {m.pagination.prev}
      </button>

      <span className="pagination-info">
        {m.pagination.pageWord}{" "}
        <span className="pagination-num">{page}</span> {m.pagination.ofWord}{" "}
        <span className="pagination-num">{totalPages}</span>
      </span>

      <button
        className="btn btn-ghost pagination-btn"
        disabled={page >= totalPages}
        onClick={() => {
          onPageChange(page + 1);
          window.scrollTo({ top: 0, behavior: "smooth" });
        }}
      >
        {m.pagination.next}
      </button>
    </nav>
  );
}
