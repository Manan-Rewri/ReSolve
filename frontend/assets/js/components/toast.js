const DEFAULT_DURATION_MS = 3200;
const LEAVE_ANIMATION_MS = 200;

const CHECK_ICON = `
<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
     stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="m5 13 4 4L19 7"/>
</svg>`;

/**
 * Shows a transient message in a bottom-anchored toast region.
 *
 * @param {HTMLElement} region container element (created in the page markup)
 * @param {{ message: string, detail?: string, duration?: number }} options
 */
export function showToast(region, { message, detail = "", duration = DEFAULT_DURATION_MS }) {
  if (!region) return;

  const toast = document.createElement("div");
  toast.className = "toast";
  toast.setAttribute("role", "status");

  const icon = document.createElement("span");
  icon.innerHTML = CHECK_ICON;
  toast.appendChild(icon.firstElementChild);

  const label = document.createElement("span");
  label.textContent = detail ? `${message} · ${detail}` : message;
  toast.appendChild(label);

  region.appendChild(toast);

  window.setTimeout(() => {
    toast.dataset.leaving = "true";
    window.setTimeout(() => toast.remove(), LEAVE_ANIMATION_MS);
  }, duration);
}