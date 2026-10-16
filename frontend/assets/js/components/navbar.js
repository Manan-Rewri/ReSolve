import { endSession, ROUTES } from "../core/session.js";
import { initials } from "../core/dom.js";

const LINKS = [
  {
    path: ROUTES.home,
    label: "Home",
    icon: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V20h14V9.5"/>',
  },
  {
    path: ROUTES.learn,
    label: "Learn",
    icon: '<path d="M4 5h16v14H4z"/><path d="M8 9l3 3-3 3"/><path d="M13 15h4"/>',
  },
  {
    path: ROUTES.settings,
    label: "Settings",
    icon: '<circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/>',
  },
];

export function renderNavbar(container, currentPath, user) {
  if (!container) return;

  const links = LINKS.map(({ path, label, icon }) => {
    const current = path === currentPath;
    return `
      <a class="nav-link" href="${path}"${current ? ' aria-current="page"' : ""}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icon}</svg>
        <span>${label}</span>
      </a>`;
  }).join("");

  container.innerHTML = `
    <div class="navbar-brand">ReSolve<span>.</span></div>
    <nav class="nav-list" aria-label="Main">${links}</nav>
    <div class="navbar-foot">
      <div class="navbar-user">
        <strong>${escapeHtml(user?.full_name || "Account")}</strong>
        <span class="truncate">${escapeHtml(user?.email || "")}</span>
      </div>
      <button class="btn btn-ghost btn-sm btn-block" data-sign-out type="button">Sign out</button>
    </div>`;

  container.querySelector("[data-sign-out]").addEventListener("click", () => {
    endSession();
    window.location.assign(ROUTES.landing);
  });
}

function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char])
  );
}

export { escapeHtml };