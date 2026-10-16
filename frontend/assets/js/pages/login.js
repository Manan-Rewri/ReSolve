import { ApiError, api } from "../core/api.js";
import { $, setAlert, setBusy } from "../core/dom.js";
import { ROUTES, redirectIfAuthenticated, startSession } from "../core/session.js";

redirectIfAuthenticated();

const form = $("auth-form");
const alertSlot = $("form-alert");
const submitButton = $("submit");
const passwordInput = $("password");

$("auth-submit-label").textContent = "Log in";
$("auth-heading").textContent = "Welcome back";
$("auth-subheading").textContent = "Pick up your revision queue where you left it.";
$("auth-switch").innerHTML = `New to ReSolve? <a class="link-underline" href="${ROUTES.register}">Create an account</a>`;

$("password-toggle").addEventListener("click", (event) => {
  const input = passwordInput;
  const reveal = input.type === "password";
  input.type = reveal ? "text" : "password";
  event.currentTarget.textContent = reveal ? "Hide" : "Show";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setAlert(alertSlot, "");
  setBusy(submitButton, true, "Signing in…");

  try {
    const result = await api.login({
      email: $("email").value.trim(),
      password: passwordInput.value,
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