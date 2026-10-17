import { SHEETS, DEFAULT_SHEET_ID } from "../core/sheets.js";

/**
 * Dropdown that selects which practice sheet is active.
 *
 * @param {{ trigger: HTMLElement, menu: HTMLElement, onChange: (sheet) => void }} options
 */
export function createSheetSelect({ trigger, menu, onChange }) {
  let selectedId = DEFAULT_SHEET_ID;
  let open = false;
  let activeIndex = 0;

  const triggerLabel = trigger.querySelector(".sheet-trigger-label");

  const current = () => SHEETS.find((sheet) => sheet.id === selectedId) ?? SHEETS[0];

  function setActive(index) {
    activeIndex = index;
    menu.querySelectorAll(".sheet-option").forEach((node, i) => {
      node.dataset.active = String(i === index);
    });
  }

  function syncTrigger() {
    const sheet = current();
    triggerLabel.textContent = sheet.label;
    trigger.title = sheet.hint;
    menu.querySelectorAll(".sheet-option").forEach((node) => {
      node.setAttribute("aria-selected", String(node.dataset.id === selectedId));
    });
  }

  function setOpen(next) {
    open = next;
    trigger.setAttribute("aria-expanded", String(open));
    menu.hidden = !open;
    trigger.parentElement.dataset.open = String(open);
    if (open) setActive(Math.max(0, SHEETS.findIndex((sheet) => sheet.id === selectedId)));
  }

  function select(id) {
    selectedId = id;
    syncTrigger();
    onChange(current());
  }

  function renderMenu() {
    menu.innerHTML = SHEETS.map(
      (sheet, index) => `
      <div class="sheet-option" role="option" data-id="${sheet.id}" data-index="${index}"
           aria-selected="${sheet.id === selectedId}">
        <span class="sheet-option-label">${sheet.label}</span>
        <span class="sheet-option-hint">${sheet.hint}</span>
      </div>`
    ).join("");

    menu.querySelectorAll(".sheet-option").forEach((node) => {
      node.addEventListener("click", () => {
        select(node.dataset.id);
        setOpen(false);
        trigger.focus();
      });
      node.addEventListener("mouseenter", () => setActive(Number(node.dataset.index)));
    });
  }

  trigger.addEventListener("click", () => setOpen(!open));

  trigger.addEventListener("keydown", (event) => {
    if (!open && (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      setOpen(true);
    } else if (open && event.key === "ArrowDown") {
      event.preventDefault();
      setActive((activeIndex + 1) % SHEETS.length);
    } else if (open && event.key === "ArrowUp") {
      event.preventDefault();
      setActive((activeIndex - 1 + SHEETS.length) % SHEETS.length);
    } else if (open && event.key === "Escape") {
      setOpen(false);
    } else if (open && event.key === "Enter") {
      event.preventDefault();
      select(SHEETS[activeIndex].id);
      setOpen(false);
    }
  });

  document.addEventListener("click", (event) => {
    if (open && !trigger.parentElement.contains(event.target)) setOpen(false);
  });

  renderMenu();
  syncTrigger();

  return {
    get sheet() {
      return current();
    },
    close: () => setOpen(false),
  };
}