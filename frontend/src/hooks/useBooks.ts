import { useCallback, useEffect, useState } from "react";
import { fetchBooks } from "../api/books";
import type { Locale } from "../i18n/locale";
import type { Book, BooksResponse, LibraryListSort } from "../types";

interface UseBooksReturn {
  books: Book[];
  total: number;
  page: number;
  totalPages: number;
  loading: boolean;
  error: string | null;
  setPage: (p: number) => void;
  refresh: () => void;
}

export function useBooks(
  locale: Locale,
  perPage = 12,
  sort: LibraryListSort = "default",
): UseBooksReturn {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<BooksResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refresh = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchBooks(locale, page, perPage, "", sort)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [locale, page, perPage, sort, tick]);

  return {
    books: data?.books ?? [],
    total: data?.total ?? 0,
    page: data?.page ?? page,
    totalPages: data?.total_pages ?? 1,
    loading,
    error,
    setPage,
    refresh,
  };
}
