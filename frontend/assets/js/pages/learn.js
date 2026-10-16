import { ApiError, api } from "../core/api.js";
import { $, setAlert, setBusy, show } from "../core/dom.js";
import { renderNavbar, escapeHtml } from "../components/navbar.js";
import { createProblemSearch } from "../components/problem-search.js";
import { requireAuth, ROUTES } from "../core/session.js";

const user = requireAuth();
if (user) renderNavbar($("navbar"), ROUTES.learn, user);

const CPP_TEMPLATE = `#include <iostream>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read from the "Standard input" panel.
    int a, b;
    cin >> a >> b;
    cout << a + b << "\\n";
    return 0;
}
`;

const workspace = $("workspace");
const emptyState = $("empty-state");
const search = createProblemSearch({
  form: $("search-form"),
  input: $("problem-input"),
  dropdown: $("suggestions"),
  onSelect: loadProblem,
});

let currentProblem = null;

function resetWorkspace() {
  currentProblem = null;
  show(emptyState, true);
  show(workspace, false);
}

async function loadProblem(titleOrUrl, suggestion) {
  setAlert($("page-alert"), "");
  setBusy($("load-button"), true, "Loading…");

  try {
    currentProblem = await api.fetchLeetCode(titleOrUrl);
    search.clear();
    renderProblem(currentProblem);
    show(emptyState, false);
    show(workspace, true);
  } catch (error) {
    const message =
      error instanceof ApiError ? error.message : "Could not load that problem.";
    setAlert($("page-alert"), message, "error");
    if (suggestion) search.clear();
  } finally {
    setBusy($("load-button"), false);
  }
}

function renderProblem(problem) {
  const topics = (problem.all_topics || []).slice(0, 8);

  setTextSafe($("statement-number"), problem.frontend_id ? `#${problem.frontend_id}` : "");
  setTextSafe($("statement-title"), problem.title || "Untitled");
  setTextSafe($("statement-difficulty"), problem.difficulty || "");
  $("statement-difficulty").className = `tag ${
    (problem.difficulty || "").toLowerCase() === "hard" ? "tag-inverted" : ""
  }`;
  $("statement-link").href = problem.url || "#";

  $("statement-tags").innerHTML = topics
    .map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`)
    .join("");

  $("statement-body").innerHTML =
    problem.content_html || `<p>No statement was returned for this problem.</p>`;

  if (!$("code-editor").value.trim()) {
    $("code-editor").value = CPP_TEMPLATE;
  }

  clearRunResult();
}

function setTextSafe(element, value) {
  if (element) element.textContent = value ?? "";
}

function clearRunResult() {
  $("editor-pane").classList.remove("pane-flagged");
  $("output").textContent = "Run your code to see the output.";
  $("output").className = "output-pane output-ok";
  $("output-badge").textContent = "";
  $("output-badge").className = "badge hidden";
  $("run-meta").textContent = "";
  $("run-status").textContent = "";
}

function flagFailure(description) {
  $("editor-pane").classList.add("pane-flagged");
  $("output-badge").textContent = description;
  $("output-badge").className = "badge";
  $("output").className = "output-pane output-error";
}

function buildOutput(result) {
  const parts = [];
  if (result.compile_output) parts.push(result.compile_output.trimEnd());
  if (result.stderr) parts.push(result.stderr.trimEnd());
  if (result.message) parts.push(result.message.trimEnd());
  if (result.stdout) parts.push(result.stdout.trimEnd());
  return parts.join("\n") || "(no output)";
}

async function runCode() {
  const source = $("code-editor").value;

  if (!source.trim()) {
    flagFailure("Nothing to run");
    $("output").textContent = "Write some code first.";
    return;
  }

  setAlert($("page-alert"), "");
  setBusy($("run-button"), true, "Running…");
  $("run-status").textContent = "Running…";
  $("editor-pane").classList.remove("pane-flagged");

  try {
    const result = await api.execute({
      language: $("language-select").value,
      source_code: source,
      stdin: $("stdin-input").value,
    });

    $("output").textContent = buildOutput(result);

    if (result.succeeded) {
      $("output-badge").textContent = result.status?.description || "Accepted";
      $("output-badge").className = "badge badge-outline";
      $("run-status").textContent = "Ran successfully";
    } else {
      flagFailure(result.status?.description || "Error");
      $("run-status").textContent = "Finished with errors";
    }

    const meta = [];
    if (typeof result.time === "number") meta.push(`time ${result.time}s`);
    if (typeof result.memory === "number") meta.push(`memory ${result.memory} KB`);
    if (result.exit_code !== null && result.exit_code !== undefined) {
      meta.push(`exit ${result.exit_code}`);
    }
    $("run-meta").textContent = meta.join(" · ");
  } catch (error) {
    flagFailure("Request failed");
    $("output").textContent = error.message;
    $("run-status").textContent = "Failed";
  } finally {
    setBusy($("run-button"), false);
  }
}

async function saveProblem() {
  if (!currentProblem) return;

  setAlert($("page-alert"), "");
  setBusy($("save-button"), true, "Saving…");

  try {
    await api.saveProblem({
      url: currentProblem.url,
      title: currentProblem.title,
      topic: currentProblem.topic || "Algorithms",
      difficulty: currentProblem.difficulty || "Medium",
      content_html: currentProblem.content_html,
    });
    setAlert($("page-alert"), "Saved. It will appear in your revision queue on Home.", "success");
  } catch (error) {
    setAlert($("page-alert"), error.message, "error");
  } finally {
    setBusy($("save-button"), false);
  }
}

async function loadLanguages() {
  const select = $("language-select");
  try {
    const languages = await api.languages();
    select.replaceChildren();
    languages.forEach((language) => {
      const option = document.createElement("option");
      option.value = language.id;
      option.textContent = language.label;
      select.appendChild(option);
    });
    select.value = "cpp";
  } catch {
    select.replaceChildren();
    const fallback = document.createElement("option");
    fallback.value = "cpp";
    fallback.textContent = "C++";
    select.appendChild(fallback);
  }
}

$("code-editor").addEventListener("keydown", (event) => {
  if (event.key === "Tab") {
    event.preventDefault();
    const editor = event.currentTarget;
    const start = editor.selectionStart;
    editor.value = `${editor.value.slice(0, start)}  ${editor.value.slice(editor.selectionEnd)}`;
    editor.selectionStart = editor.selectionEnd = start + 2;
  }
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    runCode();
  }
});

$("run-button").addEventListener("click", runCode);
$("save-button").addEventListener("click", saveProblem);
$("reset-button").addEventListener("click", resetWorkspace);

resetWorkspace();
loadLanguages();