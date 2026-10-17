import { api } from "./api.js";

/**
 * Practice sheets available in the Home search dropdown.
 *
 * The sheet id is sent to the backend, which filters suggestions down to that
 * sheet's problem set. To add a sheet, define it in
 * `backend/app/services/sheets.py` and list it here - nothing else changes.
 */
export const SHEETS = [
  { id: "all", label: "All problems", hint: "Every LeetCode problem" },
  { id: "striver", label: "Striver A2Z DSA", hint: "Striver's step-wise DSA sheet" },
  { id: "leetcode", label: "LeetCode DSA", hint: "Core LeetCode DSA patterns" },
];

export const DEFAULT_SHEET_ID = "all";

export function getSheet(id) {
  return SHEETS.find((sheet) => sheet.id === id) ?? SHEETS[0];
}

/** Searches within one sheet. */
export function searchSheet(sheetId, term, signal) {
  return api.searchProblems(term, 8, sheetId, signal);
}