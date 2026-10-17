import { ApiError, api } from "../core/api.js";
import { $, setAlert, setBusy, show } from "../core/dom.js";
import { renderNavbar, escapeHtml } from "../components/navbar.js";
import { createProblemSearch } from "../components/problem-search.js";
import { showToast } from "../components/toast.js";
import { sampleToStdin, templateFor } from "../core/templates.js";
import { requireAuth, ROUTES } from "../core/session.js";

const user = requireAuth();
if (user) renderNavbar($("navbar"), ROUTES.learn, user);

const editor = $("code-editor");
const languageSelect = $("language-select");
let editorIsTemplate = true;

function applyTemplate() {
  editor.value = templateFor(languageSelect.value);
  editorIsTemplate = true;
  clearRunResult();
}

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

  renderExamples(problem.examples || []);

  if (editorIsTemplate || !editor.value.trim()) {
    applyTemplate();
  }

  if (!$("stdin-input").value.trim()) {
    $("stdin-input").value = sampleToStdin(problem.sample_test_case);
  }

  clearRunResult();
}

/**
 * Shows LeetCode's own examples under the statement. Clicking one loads it into
 * Standard input and pre-fills the terminal's expected output, which is the
 * quickest way to try an answer.
 */
function renderExamples(examples) {
  const block = $("examples-block");
  const list = $("examples-list");

  if (!examples.length) {
    block.classList.add("hidden");
    return;
  }

  list.innerHTML = examples
    .map(
      (example, index) => `
      <button class="example" type="button" data-index="${index}">
        <span class="example-title">
          Example ${index + 1}
          <span class="example-hint">click to use</span>
        </span>
        <span class="example-row">
          <span class="example-key">Input</span>
          <span class="example-value">${escapeHtml(example.input)}</span>
        </span>
        <span class="example-row">
          <span class="example-key">Output</span>
          <span class="example-value">${escapeHtml(example.output)}</span>
        </span>
      </button>`
    )
    .join("");

  list.querySelectorAll(".example").forEach((node) => {
    node.addEventListener("click", () => {
      const index = Number(node.dataset.index);
      $("stdin-input").value = sampleToStdin(examples[index].input);
      $("terminal-expected").value = examples[index].output || "";
      showToast($("toast-region"), { message: `Example ${index + 1} loaded` });
    });
  });

  block.classList.remove("hidden");
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

/**
 * Splits output into comparable tokens so LeetCode's "[0,1]" and the driver's
 * plain "0 1" count as the same answer. Brackets, quotes, commas and whitespace
 * are ignored; ordering still matters.
 */
function outputTokens(text) {
  return String(text || "")
    .replace(/[[\]{}()"'`,]/g, " ")
    .split(/\s+/)
    .map((token) => token.trim())
    .filter(Boolean);
}

let lastRun = { actual: "", succeeded: false };

/** The expected answer: whatever the terminal holds, else the problem's Example 1. */
function expectedForVerdict() {
  return $("terminal-expected").value.trim() || currentProblem?.sample_expected_output || "";
}

/** "Failed" | "Ran successfully" | "Correct" | "Incorrect". */
function verdictFor(actual, succeeded) {
  if (!succeeded) return "Failed";

  const expected = expectedForVerdict();
  if (!expected) return "Ran successfully";

  const actualTokens = outputTokens(actual);
  const expectedTokens = outputTokens(expected);
  return actualTokens.length === expectedTokens.length &&
    actualTokens.every((token, index) => token === expectedTokens[index])
    ? "Correct"
    : "Incorrect";
}

function badgeClassFor(verdict) {
  return verdict === "Correct" || verdict === "Ran successfully"
    ? "badge badge-outline"
    : "badge";
}

function judgeOutput() {
  const badge = $("terminal-verdict");
  const verdict = verdictFor(lastRun.actual, lastRun.succeeded);
  badge.textContent = verdict;
  badge.className = badgeClassFor(verdict);
}

function openTerminal({ stdin, output, expected, meta }) {
  $("terminal-input").textContent = stdin.trim() || "(empty)";
  $("terminal-output").textContent = output;
  $("terminal-expected").value = expected || "";
  $("terminal-expected-hint").textContent = expected
    ? "from Example 1 — edit if your format differs"
    : "no expected output found for this problem";
  $("terminal-meta").textContent = meta;

  judgeOutput();
  $("terminal-backdrop").classList.remove("hidden");
  $("terminal-close").focus();
}

function closeTerminal() {
  $("terminal-backdrop").classList.add("hidden");
}

$("terminal-close").addEventListener("click", closeTerminal);
$("terminal-backdrop").addEventListener("click", (event) => {
  if (event.target === $("terminal-backdrop")) closeTerminal();
});
$("terminal-expected").addEventListener("input", judgeOutput);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !$("terminal-backdrop").classList.contains("hidden")) {
    closeTerminal();
  }
});

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

    const printed = result.stdout ?? "";
    const succeeded = result.succeeded === true;
    const verdict = verdictFor(printed, succeeded);

    // The box shows only what the program printed. Compiler output and stderr
    // stay in the terminal and the flagged editor so they never pollute it.
    $("output").textContent = succeeded
      ? printed || "(the program printed nothing)"
      : buildOutput(result);
    $("output").className = `output-pane ${
      verdict === "Correct" || verdict === "Ran successfully" ? "output-ok" : "output-error"
    }`;

    $("output-badge").textContent = verdict;
    $("output-badge").className = badgeClassFor(verdict);

    if (succeeded) {
      $("editor-pane").classList.remove("pane-flagged");
      $("run-status").textContent = verdict;
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

    lastRun = { actual: printed, succeeded };
    openTerminal({
      stdin: $("stdin-input").value,
      output: buildOutput(result),
      expected: expectedForVerdict(),
      meta: meta.join(" · "),
    });
  } catch (error) {
    flagFailure("Request failed");
    $("output").textContent = error.message;
    $("run-status").textContent = "Failed";

    lastRun = { actual: "", succeeded: false };
    openTerminal({
      stdin: $("stdin-input").value,
      output: error.message,
      expected: expectedForVerdict(),
      meta: "execution request failed",
    });
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
    const target = event.currentTarget;
    const start = target.selectionStart;
    target.value = `${target.value.slice(0, start)}  ${target.value.slice(target.selectionEnd)}`;
    target.selectionStart = target.selectionEnd = start + 2;
    editorIsTemplate = false;
  }
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    runCode();
  }
});

editor.addEventListener("input", () => {
  editorIsTemplate = false;
  if (editor.classList.contains("has-error")) setEditorError(false);
});

// Choosing a different language swaps in that language's starter code.
languageSelect.addEventListener("change", applyTemplate);

$("run-button").addEventListener("click", runCode);
$("save-button").addEventListener("click", saveProblem);
$("template-button").addEventListener("click", () => {
  applyTemplate();
  showToast($("toast-region"), { message: "Starter template restored" });
});
$("reset-button").addEventListener("click", resetWorkspace);

resetWorkspace();
applyTemplate();
loadLanguages();

// Arriving from Home with ?q=Two%20Sum loads that problem straight away.
const requestedProblem = new URLSearchParams(window.location.search).get("q");
if (requestedProblem) {
  loadProblem(requestedProblem, null);
  window.history.replaceState({}, "", ROUTES.learn);
}