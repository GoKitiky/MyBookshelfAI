import { useEffect, useState } from "react";
import { fetchSettings, saveSettings, testConnection } from "../api/settings";
import { useToast } from "../components/Toast";
import { useI18n } from "../i18n/I18nContext";
import type { AppSettings } from "../types";
import "./SettingsPage.css";

const settingsMessages = {
  en: {
    title: "Settings",
    providerPresets: "Provider presets",
    apiKey: "API Key",
    baseUrl: "Base URL",
    modelOnline: "Online model",
    modelOffline: "Offline model",
    testConnection: "Test Connection",
    testing: "Testing…",
    save: "Save",
    saving: "Saving…",
    showKey: "Show API key",
    hideKey: "Hide API key",
    testSuccess: "Connection successful!",
    testFailed: (err: string) => `Connection failed: ${err}`,
    saveSuccess: "Settings saved!",
    saveFailed: (err: string) => `Failed to save: ${err}`,
    loadFailed: (err: string) => `Failed to load settings: ${err}`,
  },
  ru: {
    title: "Настройки",
    providerPresets: "Провайдеры",
    apiKey: "API-ключ",
    baseUrl: "Base URL",
    modelOnline: "Онлайн модель",
    modelOffline: "Оффлайн модель",
    testConnection: "Проверить соединение",
    testing: "Проверка…",
    save: "Сохранить",
    saving: "Сохранение…",
    showKey: "Показать API-ключ",
    hideKey: "Скрыть API-ключ",
    testSuccess: "Соединение успешно!",
    testFailed: (err: string) => `Ошибка соединения: ${err}`,
    saveSuccess: "Настройки сохранены!",
    saveFailed: (err: string) => `Не удалось сохранить: ${err}`,
    loadFailed: (err: string) => `Не удалось загрузить настройки: ${err}`,
  },
} as const;

const PRESETS = [
  { label: "RouterAI", baseUrl: "https://routerai.ru/api/v1" },
  { label: "OpenAI", baseUrl: "https://api.openai.com/v1" },
  { label: "OpenRouter", baseUrl: "https://openrouter.ai/api/v1" },
] as const;

export function SettingsPage() {
  const { locale } = useI18n();
  const { toast } = useToast();
  const t = settingsMessages[locale];

  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [modelProfile, setModelProfile] = useState("");
  const [modelRecommend, setModelRecommend] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettings()
      .then((s: AppSettings) => {
        setApiKey(s.api_key);
        setBaseUrl(s.base_url);
        setModelProfile(s.model_profile);
        setModelRecommend(s.model_recommend);
      })
      .catch((err: unknown) => {
        toast(t.loadFailed(err instanceof Error ? err.message : String(err)));
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleTest = async () => {
    setTesting(true);
    try {
      await testConnection({
        api_key: apiKey,
        base_url: baseUrl,
        model: modelRecommend,
      });
      toast(t.testSuccess);
    } catch (err) {
      toast(t.testFailed(err instanceof Error ? err.message : String(err)));
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const saved = await saveSettings({
        api_key: apiKey,
        base_url: baseUrl,
        model_profile: modelProfile,
        model_recommend: modelRecommend,
      });
      setApiKey(saved.api_key);
      toast(t.saveSuccess);
    } catch (err) {
      toast(t.saveFailed(err instanceof Error ? err.message : String(err)));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1>{t.title}</h1>
      </div>

      <div className="settings-form">
        <section className="settings-section">
          <h2 className="settings-section-title">{t.providerPresets}</h2>
          <div className="settings-presets">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                type="button"
                className="btn btn-ghost"
                onClick={() => setBaseUrl(p.baseUrl)}
              >
                {p.label}
              </button>
            ))}
          </div>
        </section>

        <div className="settings-field">
          <label className="settings-label" htmlFor="settings-api-key">
            {t.apiKey}
          </label>
          <div className="settings-input-row">
            <input
              id="settings-api-key"
              className="settings-input"
              type={showKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              autoComplete="off"
            />
            <button
              type="button"
              className="settings-toggle-btn"
              onClick={() => setShowKey((v) => !v)}
              aria-label={showKey ? t.hideKey : t.showKey}
              title={showKey ? t.hideKey : t.showKey}
            >
              {showKey ? <EyeOffIcon /> : <EyeIcon />}
            </button>
          </div>
        </div>

        <div className="settings-field">
          <label className="settings-label" htmlFor="settings-base-url">
            {t.baseUrl}
          </label>
          <input
            id="settings-base-url"
            className="settings-input"
            type="text"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://api.openai.com/v1"
          />
        </div>

        <div className="settings-field">
          <label className="settings-label" htmlFor="settings-model-recommend">
            {t.modelOnline}
          </label>
          <input
            id="settings-model-recommend"
            className="settings-input"
            type="text"
            value={modelRecommend}
            onChange={(e) => setModelRecommend(e.target.value)}
            placeholder="gpt-4o-mini"
          />
        </div>

        <div className="settings-field">
          <label className="settings-label" htmlFor="settings-model-profile">
            {t.modelOffline}
          </label>
          <input
            id="settings-model-profile"
            className="settings-input"
            type="text"
            value={modelProfile}
            onChange={(e) => setModelProfile(e.target.value)}
            placeholder="gpt-4o-mini"
          />
        </div>

        <div className="settings-actions">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => void handleTest()}
            disabled={testing}
          >
            {testing ? <span className="spinner" /> : null}
            {testing ? t.testing : t.testConnection}
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void handleSave()}
            disabled={saving}
          >
            {saving ? <span className="spinner" /> : null}
            {saving ? t.saving : t.save}
          </button>
        </div>
      </div>
    </div>
  );
}

function EyeIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}
