import { useEffect, useMemo, useState } from "react";
import { MetaResponse, PlanRequest, Preset } from "../api/types";

interface Props {
  meta: MetaResponse | null;
  loading: boolean;
  planning: boolean;
  onSubmit: (payload: PlanRequest) => void;
  onSavePreset: (payload: PlanRequest) => void;
  onLoadPresets: () => void;
  presets: Preset[];
  onApplyPreset: (preset: Preset) => void;
  userId: string;
  onUserIdChange: (v: string) => void;
}

function PlannerForm({
  meta,
  loading,
  planning,
  onSubmit,
  onSavePreset,
  onLoadPresets,
  presets,
  onApplyPreset,
  userId,
  onUserIdChange,
}: Props) {
  const defaults = meta?.defaults;
  const [lastSaved, setLastSaved] = useState<string | null>(() =>
    localStorage.getItem("fisher_last_saved")
  );

  const [regionId, setRegionId] = useState(defaults?.region_id || "");
  const [areaId, setAreaId] = useState(defaults?.area_id || "");
  const [species, setSpecies] = useState<string[]>([]);
  const [startDate, setStartDate] = useState(() =>
    new Date().toISOString().slice(0, 10)
  );
  const [endDate, setEndDate] = useState(() =>
    new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
  );

  const areas = useMemo(() => {
    const region = meta?.regions.find((r) => r.id === regionId);
    return region?.areas || [];
  }, [meta, regionId]);

  // Keep defaults in sync after meta load
  useEffect(() => {
    if (defaults && !regionId) {
      setRegionId(defaults.region_id);
      setAreaId(defaults.area_id);
    }
  }, [defaults, regionId]);

  const handleSpeciesToggle = (sp: string) => {
    setSpecies((prev) =>
      prev.includes(sp) ? prev.filter((s) => s !== sp) : [...prev, sp]
    );
  };

  if (loading) {
    return <p>Loading coastline metadata...</p>;
  }

  return (
    <div className="grid">
      <div className="field">
        <label>Region</label>
        <select
          value={regionId}
          onChange={(e) => {
            setRegionId(e.target.value);
            const regionAreas = meta?.regions.find((r) => r.id === e.target.value)
              ?.areas;
            if (regionAreas && regionAreas.length) {
              setAreaId(regionAreas[0].id);
            }
          }}
        >
          <option value="">Select region</option>
          {meta?.regions.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label>Area / Coastline</label>
        <select
          value={areaId}
          onChange={(e) => setAreaId(e.target.value)}
          disabled={!regionId}
        >
          <option value="">Select area</option>
          {areas.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
        {areas.length === 0 && <small>Select a region to load areas</small>}
      </div>

      <div className="field">
        <label>Dates (today + future only)</label>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            type="date"
            value={startDate}
            min={new Date().toISOString().slice(0, 10)}
            onChange={(e) => setStartDate(e.target.value)}
          />
          <input
            type="date"
            value={endDate}
            min={startDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>
      </div>

      <div className="field" style={{ gridColumn: "1 / -1" }}>
        <label>Target species (multi-select)</label>
        <div className="species-chips">
          {meta?.species.map((sp) => (
            <button
              key={sp}
              type="button"
              onClick={() => handleSpeciesToggle(sp)}
              className="chip"
              style={{
                borderColor: species.includes(sp)
                  ? "var(--accent)"
                  : "rgba(255,255,255,0.12)",
                color: species.includes(sp) ? "var(--accent)" : "var(--text)",
              }}
            >
              {sp}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
        <button
          className="btn"
          onClick={() =>
            onSubmit({ region_id: regionId, area_id: areaId, species, start_date: startDate, end_date: endDate })
          }
          disabled={planning || !regionId || !areaId}
        >
          {planning ? "Crunching..." : "Get ranked plan"}
        </button>
        <button
          className="btn secondary"
          onClick={() => {
            setSpecies([]);
            setRegionId(defaults?.region_id || "");
            setAreaId(defaults?.area_id || "");
          }}
        >
          Reset
        </button>
      </div>

      <div className="field" style={{ marginTop: 8 }}>
        <label>Account (optional for presets)</label>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input
            type="text"
            placeholder="email or nickname"
            value={userId}
            onChange={(e) => onUserIdChange(e.target.value)}
            style={{ flex: 1, minWidth: 200 }}
          />
          <button className="btn secondary" type="button" onClick={onLoadPresets}>
            Load presets
          </button>
          <button
            className="btn secondary"
            type="button"
            onClick={() =>
              (() => {
                onSavePreset({
                  region_id: regionId,
                  area_id: areaId,
                  species,
                  start_date: startDate,
                  end_date: endDate,
                });
                const ts = new Date().toISOString();
                localStorage.setItem("fisher_last_saved", ts);
                setLastSaved(ts);
              })()
            }
          >
            Save preset
          </button>
        </div>
        {presets.length === 0 && (
          <small style={{ color: "var(--muted)" }}>
            No presets saved yet. Set a user ID and click “Save preset”.
          </small>
        )}
        {presets.length > 0 && (
          <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
            {presets.map((p, idx) => (
              <button
                key={idx}
                className="chip"
                type="button"
                onClick={() => {
                  setRegionId(p.region_id);
                  setAreaId(p.area_id);
                  setSpecies(p.species);
                  setStartDate(p.start_date);
                  setEndDate(p.end_date);
                  onApplyPreset(p);
                  setLastSaved(new Date().toISOString());
                }}
              >
                {p.region_id} / {p.area_id} ({p.species.join(", ") || "all"})
              </button>
            ))}
          </div>
        )}
        {lastSaved && (
          <small style={{ color: "var(--muted)" }}>
            Last saved: {new Date(lastSaved).toLocaleString()}
          </small>
        )}
      </div>
    </div>
  );
}

export default PlannerForm;
