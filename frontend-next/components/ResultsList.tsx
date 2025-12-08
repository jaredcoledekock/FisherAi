import { useMemo, useState } from "react";
import { Area, PlanWindow } from "../lib/types";
import { sendFeedback } from "../lib/api";

interface Props {
  results: PlanWindow[];
  area?: Area;
  userId: string;
}

const clamp = (n: number, min: number, max: number) =>
  Math.min(max, Math.max(min, n));

function MetricBar({
  label,
  value,
  min,
  max,
  unit,
  tone = "accent",
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  unit: string;
  tone?: "accent" | "orange";
}) {
  const pct = ((clamp(value, min, max) - min) / (max - min)) * 100;
  return (
    <div className="metric">
      <div className="metric-label">
        <span>{label}</span>
        <strong>
          {value.toFixed(1)} {unit}
        </strong>
      </div>
      <div className="metric-bar">
        <div
          className="metric-fill"
          style={{
            width: `${pct}%`,
            background: tone === "orange" ? "var(--accent-2)" : "var(--accent)",
          }}
        />
      </div>
    </div>
  );
}

export default function ResultsList({ results, area, userId }: Props) {
  const [feedbackStatus, setFeedbackStatus] = useState<Record<string, string>>({});

  const topScore = useMemo(() => (results[0] ? results[0].score : 0), [results]);

  if (!results.length) {
    return <p style={{ color: "var(--muted)" }}>Run a plan to see ranked times.</p>;
  }

  const handleFeedback = async (row: PlanWindow, rating: "up" | "down") => {
    const key = `${row.date}-${row.window_id}`;
    setFeedbackStatus((prev) => ({ ...prev, [key]: "Sending..." }));
    try {
      await sendFeedback(userId || null, {
        rating,
        date: row.date,
        window_id: row.window_id,
        window: row.window,
        score: row.score,
        per_species: row.per_species,
        sources: row.sources,
      });
      setFeedbackStatus((prev) => ({ ...prev, [key]: "Thanks!" }));
    } catch (err) {
      setFeedbackStatus((prev) => ({ ...prev, [key]: "Error" }));
    }
  };

  return (
    <div className="results">
      <div className="result-meta">
        <div>
          <div className="badge">Top ranked windows</div>
          {area && (
            <p style={{ margin: "6px 0", color: "var(--muted)" }}>
              {area.name} • Facing {area.coast_facing} • {area.notes}
            </p>
          )}
        </div>
        <div className="score">{topScore.toFixed(0)} pts</div>
      </div>

      <div className="grid">
        {results.slice(0, 8).map((row) => {
          const key = `${row.date}-${row.window_id}`;
          const hasGap =
            !row.sources ||
            !row.sources.wind ||
            !row.sources.swell ||
            !row.sources.sea_temp ||
            !row.sources.tide;

          return (
            <div key={key} className="result-card">
              <div className="result-meta">
                <strong>
                  {new Date(row.date).toLocaleDateString(undefined, {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                  })}{" "}
                  · {row.window}
                </strong>
                <span className="badge">Score {row.score.toFixed(0)}</span>
              </div>
              <div className="species-chips">
                {row.per_species.map((sp) => (
                  <span key={sp.species} className="chip">
                    {sp.species}: {sp.label}
                  </span>
                ))}
              </div>

              <div className="metrics-row">
                <MetricBar label="Wind" value={row.wind_speed} min={0} max={30} unit="kt" />
                <MetricBar
                  label="Swell"
                  value={row.swell_height}
                  min={0}
                  max={4}
                  unit="m"
                  tone="orange"
                />
              </div>

              <p style={{ margin: "8px 0", color: "var(--muted)", fontSize: 13 }}>
                Dir {row.wind_deg.toFixed(0)}° · Period {row.swell_period.toFixed(1)}s · Sea{" "}
                {row.sea_temp.toFixed(1)}°C · Tide {row.tide_phase}
              </p>

              <p style={{ margin: "6px 0", color: "var(--muted)", fontSize: 12 }}>
                {row.explanation}
              </p>

              {row.sources && (
                <div className="species-chips" style={{ marginTop: 4 }}>
                  <span className="chip">Wind: {row.sources.wind || "open-meteo"}</span>
                  <span className="chip">Swell: {row.sources.swell || "open-meteo"}</span>
                  <span className="chip">Temp: {row.sources.sea_temp || "open-meteo"}</span>
                  <span className="chip">Tide: {row.sources.tide || "open-meteo"}</span>
                </div>
              )}
              {hasGap && (
                <div className="species-chips" style={{ marginTop: 4 }}>
                  <span className="chip" style={{ borderColor: "#ffb057", color: "#ffb057" }}>
                    Data gap: fallback used
                  </span>
                </div>
              )}

              {row.factors && row.factors.length > 0 && (
                <div className="species-chips" style={{ marginTop: 6 }}>
                  {row.factors.map((f) => (
                    <span key={f} className="chip">
                      {f}
                    </span>
                  ))}
                </div>
              )}

              <div className="feedback">
                <span style={{ color: "var(--muted)", fontSize: 12 }}>
                  Feedback this ranking?
                </span>
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="chip" onClick={() => handleFeedback(row, "up")}>
                    👍 Accurate
                  </button>
                  <button className="chip" onClick={() => handleFeedback(row, "down")}>
                    👎 Off
                  </button>
                  <span style={{ color: "var(--muted)", fontSize: 12 }}>
                    {feedbackStatus[key] || ""}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
