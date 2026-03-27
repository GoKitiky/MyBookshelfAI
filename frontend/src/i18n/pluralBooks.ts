import type { Locale } from "./locale";

/** Слово «книга» / «book(s)» для счётчика n ≥ 0. */
export function bookWord(n: number, locale: Locale): string {
  if (locale === "en") {
    return n === 1 ? "book" : "books";
  }
  const abs = Math.abs(n) % 100;
  const n1 = abs % 10;
  if (abs > 10 && abs < 20) return "книг";
  if (n1 > 1 && n1 < 5) return "книги";
  if (n1 === 1) return "книга";
  return "книг";
}
