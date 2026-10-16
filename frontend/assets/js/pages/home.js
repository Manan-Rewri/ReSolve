import { api } from "../core/api.js";
import { $, setAlert, setText, show } from "../core/dom.js";
import { formatDate, pluralize, relativeDay } from "../core/format.js";
import { renderNavbar, escapeHtml } from "../components/navbar.js";
import { requireAuth, ROUTES } from "../core/session.js";

const user = requireAuth();
if (user) renderNavbar($("navbar"), ROUTES.home, user);

const alertSlot = $("page-alert");
const statsSlot = $("stat-grid");
const dueSlot = $("due-today-list");
const overdueSlot = $("overdue-list");
const upcomingSlot = $("upcoming-list");
const topicSlot = $("topic-bars");
const difficultySlot = $("difficulty-bars");

function renderStats(data) {
  const cards = [
    { value: data.total_saved_problems, label: "Problems saved", emphasis: false },
    { value: data.due_today_count, label: "Due today", emphasis: data.due_today_count > 0 },
    { value: data.overdue_count, label: "Overdue", emphasis: data.overdue_count > 0 },
    { value: data.mastered_count, label: "Mastered", emphasis: false },
  ];

  statsSlot.innerHTML = cards
    .map(
      (card) => `
      <div class="stat${card.emphasis ? " stat-emphasis" : ""}">
        <div class="stat-value">${card.value}</div>
        <div class="stat-label">${card.label}</div>
      </div>`
    )
    .join("");
}

function problemRows(items) {
  if (!items.length) {
    return `<p class="empty">Nothing here — you're all caught up.</p>`;
  }

  return items
    .map(
      (problem) => `
      <div class="problem-row">
        <div class="grow">
          <div class="problem-row-title">${escapeHtml(problem.title)}</div>
          <div class="problem-row-meta">
            ${escapeHtml(problem.topic)} · ${escapeHtml(problem.difficulty)} ·
            due ${escapeHtml(relativeDay(problem.next_review_due))}
          </div>
        </div>
        <span class="badge">${escapeHtml(problem.practice_priority)}/4</span>
      </div>`
    )
    .join("");
}

function renderTimeline(groups) {
  if (!groups.length) {
    upcomingSlot.innerHTML = `<p class="empty">No revisions scheduled this week.</p>`;
    return;
  }

  upcomingSlot.innerHTML = groups
    .map(
      (group) => `
      <div class="timeline-day">
        <div class="timeline-date">${escapeHtml(formatDate(group.due_date))}</div>
        <div class="timeline-count">${escapeHtml(pluralize(group.count, "problem"))}</div>
      </div>`
    )
    .join("");
}

function renderBars(records, slot) {
  const entries = Object.entries(records || {});
  if (!entries.length) {
    slot.innerHTML = `<p class="empty">No data yet.</p>`;
    return;
  }

  const max = Math.max(...entries.map(([, count]) => count), 1);
  slot.innerHTML = entries
    .sort((a, b) => b[1] - a[1])
    .map(
      ([name, count]) => `
      <div class="bar-item">
        <div class="bar-name" title="${escapeHtml(name)}">${escapeHtml(name)}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${(count / max) * 100}%"></div></div>
        <div class="bar-value">${count}</div>
      </div>`
    )
    .join("");
}

async function loadDashboard() {
  setAlert(alertSlot, "");
  show(dueSlot, false);

  try {
    const data = await api.dashboard();
    renderStats(data);
    dueSlot.innerHTML = problemRows(data.due_today);
    overdueSlot.innerHTML = problemRows(data.overdue);
    renderTimeline(data.upcoming_revisions || []);
    renderBars(data.by_topic, topicSlot);
    renderBars(data.by_difficulty, difficultySlot);
    show(dueSlot, true);
    setText($("updated-at"), `Updated ${new Date().toLocaleTimeString()}`);
  } catch (error) {
    setAlert(alertSlot, error.message, "error");
    dueSlot.innerHTML = `<p class="empty">No data available.</p>`;
    show(dueSlot, true);
  }
}

$("refresh").addEventListener("click", loadDashboard);
loadDashboard();