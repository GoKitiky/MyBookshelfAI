import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { FirstRunLocaleModal } from "../components/FirstRunLocaleModal";
import { LOCALE_STORAGE_KEY, type Locale, parseStoredLocale } from "./locale";
import { messagesByLocale, type Messages } from "./messages";
import { bookWord } from "./pluralBooks";

type I18nValue = {
  locale: Locale;
  /** Persists locale (first-run only; no in-app language switch). */
  setLocale: (locale: Locale) => void;
  m: Messages;
  bookWord: (n: number) => string;
};

const I18nContext = createContext<I18nValue | null>(null);

function readInitialLocale(): Locale | null {
  if (typeof window === "undefined") return null;
  return parseStoredLocale(localStorage.getItem(LOCALE_STORAGE_KEY));
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale | null>(readInitialLocale);

  const commitLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    try {
      localStorage.setItem(LOCALE_STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
    document.documentElement.lang = next === "ru" ? "ru" : "en";
  }, []);

  useEffect(() => {
    if (locale !== null) {
      document.documentElement.lang = locale === "ru" ? "ru" : "en";
    }
  }, [locale]);

  // Must run on every render: hook order cannot depend on locale (first-run modal vs app).
  const value = useMemo<I18nValue | null>(() => {
    if (locale === null) return null;
    const m = messagesByLocale[locale];
    return {
      locale,
      setLocale: commitLocale,
      m,
      bookWord: (n: number) => bookWord(n, locale),
    };
  }, [locale, commitLocale]);

  if (locale === null || value === null) {
    return <FirstRunLocaleModal onSelect={commitLocale} />;
  }

  return (
    <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
  );
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return ctx;
}
