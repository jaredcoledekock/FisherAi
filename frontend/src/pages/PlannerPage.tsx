import { useEffect, useMemo, useState } from "react";
import PlannerForm from "../components/PlannerForm";
import ResultsList from "../components/ResultsList";
import { usePlanner } from "../queries/usePlanner";
import { Preset, PlanRequest } from "../api/types";

function PlannerPage() {
  const {
    meta,
    loadingMeta,
    runPlan,
    results,
    planning,
    error,
    presets,
    loadPresets,
    persistPreset,
  } = usePlanner();
  const [submitted, setSubmitted] = useState(false);
  const [userId, setUserId] = useState(() => localStorage.getItem("fisher_user_id") || "");

  useEffect(() => {
    if (meta && !submitted) {
      // Auto-run for defaults on initial load
      const defaults = meta.defaults;
      if (defaults) {
        runPlan({
          region_id: defaults.region_id,
          area_id: defaults.area_id,
          species: [],
          start_date: new Date().toISOString().slice(0, 10),
          end_date: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000)
            .toISOString()
            .slice(0, 10),
        });
        setSubmitted(true);
      }
    }
  }, [meta, runPlan, submitted]);

  const handleSavePreset = (payload: PlanRequest) => {
    if (!userId) {
      alert("Add a user ID first (email or nickname).");
      return;
    }
    persistPreset(userId, payload);
  };

  const handleLoadPresets = () => {
    if (!userId) {
      alert("Add a user ID first (email or nickname).");
      return;
    }
    loadPresets(userId);
  };

  const heroCopy = useMemo(
    () => [
      "AI-ranked bite windows by region, area, species, and tide.",
      "South African coast presets: Western Cape, Eastern Cape, KZN.",
      "Multi-API blend (Open-Meteo marine + weather).",
      "Only today + future dates; honors local rule notes.",
    ],
    []
  );

  return (
    <div className="hero" id="planner">
      <div className="hero-card">
        <div className="badge">Plan your next strike</div>
        <h1 style={{ marginBottom: 8 }}>Forecast like a local</h1>
        <p style={{ color: "var(--muted)", lineHeight: 1.6 }}>
          Choose your region, area, target species, and dates. We blend marine and
          weather data with local rule notes to rank the best day/time windows.
        </p>
        <div className="grid">
          {heroCopy.map((line) => (
            <div key={line} className="card">
              <h4>{line.split(":")[0]}</h4>
              <p style={{ margin: 0, color: "var(--muted)" }}>
                {line.includes(":") ? line.split(":")[1] : ""}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="hero-card">
        <PlannerForm
          meta={meta}
          loading={loadingMeta}
          onSubmit={(payload) => {
            runPlan(payload);
            setSubmitted(true);
          }}
          planning={planning}
          onSavePreset={handleSavePreset}
          onLoadPresets={handleLoadPresets}
          presets={presets}
          userId={userId}
          onUserIdChange={(val) => {
            setUserId(val);
            localStorage.setItem("fisher_user_id", val);
          }}
          onApplyPreset={(preset: Preset) => {
            runPlan(preset);
            setSubmitted(true);
          }}
        />
        {error && <div className="alert">{error}</div>}
      </div>

      <div className="hero-card" style={{ gridColumn: "1 / -1" }}>
        <ResultsList
          results={results?.results || []}
          area={results?.area}
          userId={userId}
        />
      </div>
    </div>
  );
}

export default PlannerPage;
