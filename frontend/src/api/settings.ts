import type { AppSettings, SettingsStatus, TestConnectionResult } from "../types";

const BASE = "/api/settings";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export function fetchSettings(): Promise<AppSettings> {
  return request<AppSettings>(BASE);
}

export function saveSettings(data: Partial<AppSettings>): Promise<AppSettings> {
  return request<AppSettings>(BASE, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function testConnection(data: {
  api_key: string;
  base_url: string;
  model: string;
}): Promise<TestConnectionResult> {
  return request<TestConnectionResult>(`${BASE}/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function fetchSettingsStatus(): Promise<SettingsStatus> {
  return request<SettingsStatus>(`${BASE}/status`);
}
