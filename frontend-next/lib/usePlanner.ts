import { useCallback, useEffect, useState } from "react";
import { fetchMeta, createPlan, getPresets, savePreset } from "./api";
import { MetaResponse, PlanRequest, PlanResponse, Preset } from "./types";

export function usePlanner() {
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [loadingMeta, setLoadingMeta] = useState<boolean>(true);
  const [results, setResults] = useState<PlanResponse | null>(null);
  const [planning, setPlanning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [presets, setPresets] = useState<Preset[]>([]);

  useEffect(() => {
    (async () => {
      try {
        setLoadingMeta(true);
        const data = await fetchMeta();
        setMeta(data);
      } catch (err: any) {
        setError(err?.message || "Failed to load metadata");
      } finally {
        setLoadingMeta(false);
      }
    })();
  }, []);

  const runPlan = useCallback(async (payload: PlanRequest) => {
    try {
      setPlanning(true);
      setError(null);
      const data = await createPlan(payload);
      setResults(data);
    } catch (err: any) {
      setError(err?.response?.data?.error || err?.message || "Plan failed");
    } finally {
      setPlanning(false);
    }
  }, []);

  const loadPresets = useCallback(async (userId: string) => {
    if (!userId) return;
    try {
      const data = await getPresets(userId);
      setPresets(data);
    } catch (err: any) {
      setError(err?.response?.data?.error || err?.message || "Preset fetch failed");
    }
  }, []);

  const persistPreset = useCallback(async (userId: string, preset: Preset) => {
    if (!userId) return;
    try {
      const data = await savePreset(userId, preset);
      setPresets(data);
    } catch (err: any) {
      setError(err?.response?.data?.error || err?.message || "Preset save failed");
    }
  }, []);

  return {
    meta,
    loadingMeta,
    results,
    planning,
    runPlan,
    error,
    presets,
    loadPresets,
    persistPreset,
  };
}
