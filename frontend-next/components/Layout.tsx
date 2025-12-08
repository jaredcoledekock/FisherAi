import { ReactNode } from "react";

type Props = { children: ReactNode };

export default function Layout({ children }: Props) {
  return (
    <div className="app-shell">
      <header className="navbar">
        <div className="logo">False Bay FisherAI</div>
        <div style={{ display: "flex", gap: 12 }}>
          <a
            className="btn secondary"
            href="https://github.com/"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
        </div>
      </header>
      <main>{children}</main>
      <footer className="footer">Made for SA coastline anglers.</footer>
    </div>
  );
}
