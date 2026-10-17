import { $, setText } from "../core/dom.js";
import { ROUTES, requireAuth } from "../core/session.js";
import { renderNavbar } from "../components/navbar.js";
import { createProblemSearch } from "../components/problem-search.js";
import { createSheetSelect } from "../components/sheet-select.js";
import { searchSheet } from "../core/sheets.js";

const user = requireAuth();
if (user) {
  renderNavbar($("navbar"), ROUTES.home, user);
  // Falls back to the email address when no name was given at signup.
  setText($("home-welcome"), `Welcome, ${user.full_name || user.email}`);
}

const input = $("problem-input");
const sheetSelect = createSheetSelect({
  trigger: $("sheet-trigger"),
  menu: $("sheet-menu"),
  onChange: (sheet) => {
    input.placeholder = `Search ${sheet.label}…`;
    // A sheet change invalidates whatever is currently shown.
    if ($("suggestions").dataset.open === "true") input.dispatchEvent(new Event("input"));
  },
});

createProblemSearch({
  form: $("search-form"),
  input,
  dropdown: $("suggestions"),
  search: (term, signal) => searchSheet(sheetSelect.sheet.id, term, signal),
  onSelect: (title) => {
    // Hand the problem over to the practice workspace.
    window.location.assign(`${ROUTES.learn}?q=${encodeURIComponent(title)}`);
  },
});