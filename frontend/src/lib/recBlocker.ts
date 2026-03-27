import type { RecErrorShort } from "../i18n/messages";

export type RecBlocker =
  | { kind: "need_sync" }
  | { kind: "need_books" }
  | { kind: "need_enrich" }
  | { kind: "other" };

export function recBlockerFromMessage(message: string): RecBlocker {
  const m = message.toLowerCase();
  if (
    m.includes("no library found") ||
    m.includes("library is empty") ||
    m.includes("sync first")
  ) {
    return { kind: "need_sync" };
  }
  if (m.includes("need at least 2 books")) {
    return { kind: "need_books" };
  }
  if (m.includes("no enriched books")) {
    return { kind: "need_enrich" };
  }
  return { kind: "other" };
}

export function shortRecErrorLabel(
  blocker: RecBlocker,
  labels: RecErrorShort,
): string {
  switch (blocker.kind) {
    case "need_sync":
      return labels.need_sync;
    case "need_books":
      return labels.need_books;
    case "need_enrich":
      return labels.need_enrich;
    default:
      return labels.other;
  }
}
