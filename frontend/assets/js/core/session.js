import { api } from "./api.js";

export const ROUTES = {
  landing: "/",
  register: "/register",
  login: "/login",
  home: "/home",
  learn: "/learn",
  settings: "/settings",
};

export function go(path) {
  window.location.assign(path);
}

/** Landing and auth pages bounce signed-in users straight to /home. */
export function redirectIfAuthenticated() {
  if (api.readToken()) {
    go(ROUTES.home);
    return true;
  }
  return false;
}

/** Protected pages send signed-out visitors to /login. */
export function requireAuth() {
  if (!api.readToken()) {
    go(ROUTES.login);
    return null;
  }
  return api.user();
}

export function startSession(token, user) {
  api.persistToken(token);
  api.setUser(user);
}

export function endSession() {
  api.clearToken();
}