const DEFAULT_BASE = "http://127.0.0.1:8000/api/v1";

function resolveBase() {
  if (window.RESOLVE_API_BASE) return String(window.RESOLVE_API_BASE).replace(/\/$/, "");
  const origin = window.location.origin;
  return origin && origin.startsWith("http") ? `${origin}/api/v1` : DEFAULT_BASE;
}

const API_BASE = resolveBase();

const TOKEN_KEY = "resolve.token";
const USER_KEY = "resolve.user";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function readToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function authHeaders() {
  const token = readToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function extractMessage(payload, fallback) {
  if (!payload) return fallback;
  const detail = payload.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return fallback;
}

async function request(path, { method = "GET", body, auth = false, signal } = {}) {
  const headers = { ...(body ? { "Content-Type": "application/json" } : {}) };
  if (auth) Object.assign(headers, authHeaders());

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError(`Cannot reach the ReSolve API at ${API_BASE}.`, 0);
  }

  if (response.status === 204) return null;

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401 && auth) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
    throw new ApiError(extractMessage(payload, `Request failed (${response.status})`), response.status);
  }

  return payload;
}

const query = (params) => `?${new URLSearchParams(params).toString()}`;

export const api = {
  base: API_BASE,

  register: (payload) => request("/auth/signup", { method: "POST", body: payload }),
  login: (payload) => request("/auth/login", { method: "POST", body: payload }),
  me: () => request("/auth/me", { auth: true }),
  updateProfile: (payload) => request("/auth/me", { method: "PUT", body: payload, auth: true }),

  dashboard: () => request("/dashboard", { auth: true }),

  searchProblems: (term, limit = 8, sheet = null, signal) =>
    request(`/problems/search${query({ q: term, limit, ...(sheet ? { sheet } : {}) })}`, {
      signal,
    }),
  fetchLeetCode: (titleOrUrl) =>
    request("/problems/fetch-leetcode", { method: "POST", body: { title_or_url: titleOrUrl } }),
  saveProblem: (payload) => request("/problems", { method: "POST", body: payload, auth: true }),

  languages: () => request("/execute/languages"),
  execute: (payload) => request("/execute", { method: "POST", body: payload }),

  persistToken: (token) => localStorage.setItem(TOKEN_KEY, token),
  readToken,
  clearToken: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  user: () => {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY));
    } catch {
      return null;
    }
  },
  setUser: (user) => localStorage.setItem(USER_KEY, JSON.stringify(user)),
};

export { ApiError };