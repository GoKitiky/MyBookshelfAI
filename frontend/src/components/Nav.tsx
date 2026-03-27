import { NavLink } from "react-router-dom";
import { useI18n } from "../i18n/I18nContext";
import "./Nav.css";

const routes = [
  { to: "/", end: true as const },
  { to: "/recommendations", end: true as const },
  { to: "/profile", end: true as const },
  { to: "/settings", end: true as const },
] as const;

export function Nav() {
  const { m } = useI18n();

  const labels = [m.nav.library, m.nav.recommendations, m.nav.profile, m.nav.settings] as const;

  return (
    <header className="nav-bar">
      <div className="nav-inner">
        <NavLink to="/" className="nav-brand-link" end>
          <span className="nav-brand">{m.nav.brand}</span>
        </NavLink>
        <div className="nav-end">
          <nav className="nav-links" aria-label={m.nav.ariaMainNav}>
            {routes.map((r, i) => (
              <NavLink
                key={r.to}
                to={r.to}
                end={r.end}
                className={({ isActive }) =>
                  `nav-link ${isActive ? "nav-link--active" : ""}`
                }
              >
                {labels[i]}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>
    </header>
  );
}
