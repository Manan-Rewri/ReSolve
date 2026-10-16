import { api } from "../core/api.js";
import { $, setAlert, setBusy, setText } from "../core/dom.js";
import { formatDate } from "../core/format.js";
import { renderNavbar } from "../components/navbar.js";
import { requireAuth, ROUTES, startSession, endSession } from "../core/session.js";

const user = requireAuth();
if (user) renderNavbar($("navbar"), ROUTES.settings, user);

const alertSlot = $("page-alert");

async function loadProfile() {
  try {
    const profile = await api.me();
    $("profile-name").value = profile.full_name || "";
    setText($("profile-email"), profile.email);
    setText($("profile-joined"), formatDate(profile.created_at));
    setText($("profile-id"), profile.id);
    api.setUser(profile);
  } catch (error) {
    setAlert(alertSlot, error.message, "error");
  }
}

$("profile-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  setAlert(alertSlot, "");
  setBusy($("save-profile"), true, "Saving…");

  try {
    const updated = await api.updateProfile({ full_name: $("profile-name").value.trim() || null });
    api.setUser(updated);
    setAlert(alertSlot, "Profile updated.", "success");
  } catch (error) {
    setAlert(alertSlot, error.message, "error");
  } finally {
    setBusy($("save-profile"), false);
  }
});

$("sign-out").addEventListener("click", () => {
  endSession();
  window.location.assign(ROUTES.landing);
});

loadProfile();