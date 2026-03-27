import type { Locale } from "../i18n/locale";
import "./FirstRunLocaleModal.css";

type Props = {
  onSelect: (locale: Locale) => void;
};

/** Shown once before the app shell, before i18n context exists. */
export function FirstRunLocaleModal({ onSelect }: Props) {
  return (
    <div
      className="first-run-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="first-run-title"
    >
      <div className="first-run-card">
        <h1 id="first-run-title" className="first-run-title">
          Language
        </h1>
        <div className="first-run-actions">
          <button
            type="button"
            className="btn btn-primary first-run-btn"
            onClick={() => onSelect("ru")}
          >
            Русский
          </button>
          <button
            type="button"
            className="btn btn-primary first-run-btn"
            onClick={() => onSelect("en")}
          >
            English
          </button>
        </div>
      </div>
    </div>
  );
}
