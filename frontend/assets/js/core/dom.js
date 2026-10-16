export const $ = (id) => document.getElementById(id);

export function show(element, visible) {
  if (element) element.classList.toggle("hidden", !visible);
}

export function setText(element, value) {
  if (element) element.textContent = value ?? "";
}

/** Renders a message into a slot, using inversion to mark failure. */
export function setAlert(element, message, kind = "info") {
  if (!element) return;
  element.textContent = message || "";
  element.className = message ? `alert ${kind === "error" ? "alert-inverted" : "alert-outline"}` : "hidden";
}

export function setBusy(button, busy, busyLabel = "Working…", idleLabel = "Submit") {
  if (!button) return;
  button.disabled = busy;
  button.dataset.idleLabel = button.dataset.idleLabel || button.textContent.trim();
  button.textContent = busy ? busyLabel : button.dataset.idleLabel || idleLabel;
}

export function debounce(fn, wait = 250) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

export function initials(name, email) {
  const source = (name || email || "?").trim();
  const parts = source.split(/[\s@.]+/).filter(Boolean);
  return (parts[0]?.[0] ?? "?").concat(parts[1]?.[0] ?? "").toUpperCase();
}