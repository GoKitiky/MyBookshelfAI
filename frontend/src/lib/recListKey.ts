/** Stable key for matching recommendations to reading-list rows (title + author). */
export function recListKey(title: string, author: string): string {
  return `${title.trim().toLowerCase()}\n${author.trim().toLowerCase()}`;
}
