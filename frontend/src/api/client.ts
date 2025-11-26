import axios from "axios";
import { MetaResponse, PlanRequest, PlanResponse, Preset } from "./types";

export const API_BASE =
  (import.meta as any).env.VITE_API_BASE ||
  (import.meta as any).env.VITE_API_BASE_URL ||
  "http://localhost:5000";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
});

export async function fetchMeta(): Promise<MetaResponse> {
  const { data } = await api.get<MetaResponse>("/meta/regions");
  return data;
}

export async function createPlan(payload: PlanRequest): Promise<PlanResponse> {
  const { data } = await api.post<PlanResponse>("/plan", payload);
  return data;
}

export async function getPresets(userId: string): Promise<Preset[]> {
  const { data } = await api.get<{ presets: Preset[] }>("/user/presets", {
    headers: { "X-User-Id": userId },
  });
  return data.presets || [];
}

export async function savePreset(
  userId: string,
  payload: Preset
): Promise<Preset[]> {
  const { data } = await api.post<{ presets: Preset[] }>(
    "/user/presets",
    payload,
    { headers: { "X-User-Id": userId } }
  );
  return data.presets || [];
}

export async function sendFeedback(userId: string | null, payload: any) {
  await api.post(
    "/feedback",
    payload,
    userId ? { headers: { "X-User-Id": userId } } : undefined
  );
}

export default api;
