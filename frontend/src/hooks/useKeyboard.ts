import { useEffect } from "react";

export function useKeydown(
  key: string,
  handler: (e: KeyboardEvent) => void,
  opts?: { ctrl?: boolean; meta?: boolean; enabled?: boolean },
) {
  useEffect(() => {
    if (opts?.enabled === false) return;

    function onKeyDown(e: KeyboardEvent) {
      const ctrlMatch = opts?.ctrl ? e.ctrlKey || e.metaKey : true;
      const metaMatch = opts?.meta ? e.metaKey : true;
      if (e.key === key && ctrlMatch && metaMatch) {
        handler(e);
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [key, handler, opts?.ctrl, opts?.meta, opts?.enabled]);
}
