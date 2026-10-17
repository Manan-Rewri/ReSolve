# ReSolve — Frontend

Static, framework-free UI served directly by the FastAPI backend. No build step,
no bundler, no npm. Everything is hand-written HTML, CSS and ES modules.

## Structure

```
frontend/
├── index.html          landing          /
├── register.html                        /register
├── login.html                           /login
├── home.html          search            /home
├── learn.html         search + runner   /learn
├── settings.html                        /settings
└── assets/
    ├── css/
    │   ├── base.css    design tokens, reset, shared primitives
    │   ├── app.css     app shell + vertical navbar
    │   ├── search.css  search bar + suggestion dropdown (Home and Learn)
    │   ├── landing.css
    │   ├── auth.css    register + login
    │   ├── home.css
    │   ├── learn.css
    │   └── settings.css
    └── js/
        ├── core/       api.js · session.js · dom.js · format.js · sheets.js
        ├── components/ navbar.js · problem-search.js
        └── pages/      one entry module per page
```

## Practice sheets

`assets/js/core/sheets.js` is the single place that defines a practice sheet.
Each entry supplies its own `search(term, signal)`, so Home searches only within
the selected sheet. Today there is one sheet (`all`); adding another later is a
single entry plus a matching backend endpoint, with no changes to Home or to
the search component.

## Conventions

- Each page links only the CSS it needs, so no page pays for another's styles.
- Each page loads **one** module from `js/pages/`. Shared behaviour lives in
  `core/` (framework-free helpers) or `components/` (rendered into the page).
- All API access goes through `core/api.js`. Nothing else calls `fetch`.
- Authentication is a JWT in `localStorage` (`resolve.token`), managed by
  `core/session.js`. Never store anything else sensitive client-side.
- Guards: `redirectIfAuthenticated()` on landing/auth pages, `requireAuth()` on
  app pages.

## Design system

Monochrome by intent — black, white and greys only. Errors are flagged by
**inversion** (a black header bar and inverted badge) rather than red, which
keeps the palette minimal while still being unmistakable.

Tokens live at the top of `base.css`. Change them there and the whole app
follows:

```css
--ink: #0a0a0a;      /* primary text, borders, filled surfaces */
--paper: #ffffff;    /* page background */
--muted: #767676;    /* secondary text */
--line:  #e2e2e2;    /* hairline borders */
```

Type is **Space Grotesk**; code uses **JetBrains Mono** via
`--font-mono`. Both load from Google Fonts.

## Running

The backend serves these files, so there is nothing to build:

```powershell
cd ..\backend
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000/

> To point the UI at a different API origin, set `window.RESOLVE_API_BASE`
> before any module loads.

## Note for the designer

This is the working reference implementation. The API contract in
[`../backend/AGENTS.md`](../backend/AGENTS.md) is the source of truth — the
React app should target it rather than reverse-engineering these files.