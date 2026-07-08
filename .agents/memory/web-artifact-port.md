---
name: Web artifact port config
description: Vite dev server port history and current config for the web artifact
---

Vite dev server uses port **5173** (Vite default, supported by configureWorkflow).

**Why:** Port 22333 was originally chosen to avoid conflicts, but it is not in Replit's supported `waitForPort` list (3000, 3001, 3002, 3003, 4200, 5000, 5173, 6000, 6800, 8000, 8008, 8080, 8099, 9000). Using an unsupported port causes the workflow to report `DIDNT_OPEN_A_PORT` even when Vite starts correctly.

**How to apply:** artifact.toml `localPort = 5173` and `PORT = "5173"` in `[services.env]`. Workflow command uses `PORT=5173`. Dev script in package.json uses `fuser -k ${PORT:-5173}/tcp 2>/dev/null || true`.
