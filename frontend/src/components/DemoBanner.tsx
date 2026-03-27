import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSettingsStatus } from "../api/settings";
import { useI18n } from "../i18n/I18nContext";
import "./DemoBanner.css";

const LS_KEY = "demo_banner_dismissed";

const bannerMessages = {
  en: {
    demo: "You're exploring a demo library. Add your API key in Settings to get personalized recommendations.",
    noKey: "Add your API key in Settings to unlock AI recommendations.",
    goToSettings: "Go to Settings",
    dismiss: "Dismiss banner",
  },
  ru: {
    demo: "Вы просматриваете демо-библиотеку. Добавьте API-ключ в Настройках, чтобы получать персональные рекомендации.",
    noKey: "Добавьте API-ключ в Настройках, чтобы включить AI-рекомендации.",
    goToSettings: "Настройки",
    dismiss: "Закрыть баннер",
  },
} as const;

export function DemoBanner() {
  const { locale } = useI18n();
  const t = bannerMessages[locale];

  const [visible, setVisible] = useState(false);
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(LS_KEY) === "true") return;

    fetchSettingsStatus()
      .then((status) => {
        if (!status.has_api_key) {
          setIsDemo(status.demo_library);
          setVisible(true);
        }
      })
      .catch(() => {
        // Silently ignore — banner just won't show
      });
  }, []);

  if (!visible) return null;

  const handleDismiss = () => {
    localStorage.setItem(LS_KEY, "true");
    setVisible(false);
  };

  return (
    <div className="demo-banner" role="status">
      <span className="demo-banner__text">
        {isDemo ? t.demo : t.noKey}
      </span>
      <Link to="/settings" className="demo-banner__link">
        {t.goToSettings}
      </Link>
      <button
        type="button"
        className="demo-banner__dismiss"
        onClick={handleDismiss}
        aria-label={t.dismiss}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  );
}
