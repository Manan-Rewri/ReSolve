import { api } from "../core/api.js";
import { debounce } from "../core/dom.js";
import { escapeHtml } from "./navbar.js";

const MAX_SUGGESTIONS = 8;
const DEBOUNCE_MS = 180;

/**
 * Search bar that suggests LeetCode problems as you type.
 *
 * `search(term, signal)` scopes the lookup - pass a practice sheet's own
 * function to restrict results to that sheet. The first result is pre-selected
 * so Enter picks the top match instead of guessing a slug. Submitting with no
 * results falls back to sending the raw query.
 */
export function createProblemSearch({ form, input, dropdown, onSelect, search }) {
  const lookupSuggestions =
    search ?? ((term, signal) => api.searchProblems(term, MAX_SUGGESTIONS, null, signal));

  let items = [];
  let activeIndex = -1;
  let controller = null;

  function close() {
    dropdown.dataset.open = "false";
    dropdown.innerHTML = "";
    items = [];
    activeIndex = -1;
  }

  function highlight() {
    items.forEach((node, index) => {
      node.dataset.active = String(index === activeIndex);
    });
    items[activeIndex]?.scrollIntoView({ block: "nearest" });
  }

  function select(index) {
    const chosen = items[index];
    if (!chosen) return;
    onSelect(chosen.dataset.title, chosen.dataset);
    close();
  }

  function render(results) {
    if (!results.length) {
      close();
      return;
    }

    dropdown.innerHTML = results
      .map(
        (suggestion) => `
        <div class="suggestion" role="option"
             data-title="${escapeHtml(suggestion.title)}"
             data-slug="${escapeHtml(suggestion.title_slug)}"
             data-frontend-id="${escapeHtml(suggestion.frontend_id || "")}"
             data-difficulty="${escapeHtml(suggestion.difficulty || "")}"
             data-topic="${escapeHtml(suggestion.topic || "")}">
          <span class="suggestion-id">${escapeHtml(suggestion.frontend_id || "")}</span>
          <span class="suggestion-title">${escapeHtml(suggestion.title)}</span>
          <span class="suggestion-meta">${escapeHtml(suggestion.difficulty || "")}</span>
        </div>`
      )
      .join("");

    items = Array.from(dropdown.querySelectorAll(".suggestion"));
    items.forEach((node, index) => {
      node.addEventListener("mousedown", (event) => {
        event.preventDefault();
        select(index);
      });
    });

    // Pre-select the top hit so Enter always resolves to a real problem.
    activeIndex = 0;
    highlight();
    dropdown.dataset.open = "true";
  }

  function showStatus(message) {
    dropdown.innerHTML = `<div class="suggestion-status">${escapeHtml(message)}</div>`;
    items = [];
    activeIndex = -1;
    dropdown.dataset.open = "true";
  }

  const lookup = debounce(async (term) => {
    controller?.abort();
    controller = new AbortController();
    // LeetCode's GraphQL API can take a second or two; show feedback immediately
    // so the dropdown never looks inert while the user is still typing.
    showStatus("Searching…");

    try {
      const results = await lookupSuggestions(term, controller.signal);
      if (input.value.trim() !== term) return;
      const rows = Array.isArray(results) ? results : [];
      if (rows.length) render(rows);
      else showStatus(`No problems match “${term}”`);
    } catch (error) {
      if (error.name !== "AbortError") close();
    }
  }, DEBOUNCE_MS);

  input.addEventListener("input", () => {
    const term = input.value.trim();
    if (!term) {
      close();
      return;
    }
    lookup(term);
  });

  input.addEventListener("keydown", (event) => {
    const isOpen = dropdown.dataset.open === "true" && items.length > 0;

    if (!isOpen) {
      if (event.key === "Escape") close();
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      activeIndex = (activeIndex + 1) % items.length;
      highlight();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      activeIndex = (activeIndex - 1 + items.length) % items.length;
      highlight();
    } else if (event.key === "Enter") {
      event.preventDefault();
      select(activeIndex >= 0 ? activeIndex : 0);
    } else if (event.key === "Escape") {
      close();
    }
  });

  input.addEventListener("blur", () => setTimeout(close, 150));

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (dropdown.dataset.open === "true" && items.length) {
      select(activeIndex >= 0 ? activeIndex : 0);
      return;
    }

    const term = input.value.trim();
    if (term) {
      onSelect(term, null);
      close();
    }
  });

  return {
    close,
    clear() {
      input.value = "";
      close();
    },
  };
}