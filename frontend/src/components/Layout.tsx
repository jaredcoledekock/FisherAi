import { ReactNode, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API_BASE } from "../api/client";

type Props = { children: ReactNode };

function Layout({ children }: Props) {
  const [apiStatus, setApiStatus] = useState<"ok" | "down" | "checking">("checking");

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const res = await fetch(`${API_BASE}/meta/regions`, { method: "GET" });
        if (!res.ok) throw new Error("bad status");
        if (!cancelled) setApiStatus("ok");
      } catch (e) {
        if (!cancelled) setApiStatus("down");
      }
    };
    check();
    return () => {
      cancelled = true;
    };
  }, []);

  const statusColor =
    apiStatus === "ok" ? "var(--accent)" : apiStatus === "down" ? "#ffb057" : "var(--muted)";
  const statusLabel =
    apiStatus === "ok" ? "API live" : apiStatus === "down" ? "API offline" : "Checking...";

  return (
    <div className="app-shell">
      <header className="navbar">
        <div className="logo">False Bay FisherAI</div>
        <div style={{ display: "flex", gap: 8 }}>
          <a
            className="btn secondary"
            href="https://github.com/jaredcoledekock/FalseBayFisherAI#readme"
            target="_blank"
            rel="noreferrer"
          >
            Docs
          </a>
          <span className="chip" style={{ borderColor: statusColor, color: statusColor }}>
            {statusLabel}
          </span>
          <Link className="btn" to="#planner">
            Launch Planner
          </Link>
        </div>
      </header>
      <main>{children}</main>
      <footer className="footer">
        Built for SA coastlines • Presets optional: set an ID and use “Save/Load presets”.
      </footer>
    </div>
  );
}

export default Layout;
