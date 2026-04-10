const DESKTOP_BACKEND_URL = "http://127.0.0.1:8315";
const ABSOLUTE_URL = /^https?:\/\//i;

type TauriWindow = Window & {
  __TAURI_INTERNALS__?: unknown;
  __TAURI__?: unknown;
};

export function isDesktopTauri(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  const tauriWindow = window as TauriWindow;
  return (
    tauriWindow.__TAURI_INTERNALS__ !== undefined ||
    tauriWindow.__TAURI__ !== undefined
  );
}

export function apiUrl(path: string): string {
  if (ABSOLUTE_URL.test(path)) {
    return path;
  }
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (!isDesktopTauri()) {
    return normalized;
  }
  return `${DESKTOP_BACKEND_URL}${normalized}`;
}
