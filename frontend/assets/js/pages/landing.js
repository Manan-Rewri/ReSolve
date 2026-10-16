import { ROUTES, redirectIfAuthenticated } from "../core/session.js";

redirectIfAuthenticated();

document.getElementById("cta-register").href = ROUTES.register;
document.getElementById("cta-login").href = ROUTES.login;