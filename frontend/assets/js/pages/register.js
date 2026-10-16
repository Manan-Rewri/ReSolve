import { ApiError, api } from "../core/api.js";
import { $, setAlert, setBusy } from "../core/dom.js";
import { ROUTES, redirectIfAuthenticated, startSession } from "../core/session.js";

redirectIfAuthenticated();

const form = $("auth-form");
const alertSlot = $("form-alert");
const submitButton = $("submit");
const passwordInput = $("password");

$("auth-submit-label").textContent = "Create account";
$("auth-heading").textContent = "Create your account";
$("auth-subheading").textContent = "Start tracking what you solve and what you forget.";
$("auth-switch").innerHTML = `Already have an account? <a class="link-underline" href="${ROUTES.login}">Log in</a>`;

$("password-toggle").addEventListener("click", (event) => {
  const input = passwordInput;
  const reveal = input.type === "password";
  input.type = reveal ? "text" : "password";
  event.currentTarget.textContent = reveal ? "Hide" : "Show";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setAlert(alertSlot, "");
  setBusy(submitButton, true, "Creating…");

  try {
    const result = await api.register({
      email: $("email").value.trim(),
      password: passwordInput.value,
      full_name: $("full-name").value.trim() || null,
    });
    startSession(result.access_token, result.user);
    window.location.assign(ROUTES.home);
  } catch (error) {
    const message =
      error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
    setAlert(alertSlot, message, "error");
    setBusy(submitButton, false);
  }
});