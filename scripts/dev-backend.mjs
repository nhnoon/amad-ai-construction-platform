import { spawn } from 'node:child_process';
import net from 'node:net';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const rootDir = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const backendDir = resolve(rootDir, 'backend');

function getFreePort(startPort) {
  return new Promise((resolve, reject) => {
    const tryPort = (port) => {
      const server = net.createServer();
      server.once('error', (error) => {
        if (error && (error.code === 'EADDRINUSE' || error.code === 'EACCES')) {
          if (port < 65535) {
            tryPort(port + 1);
          } else {
            reject(new Error('Unable to find a free port'));
          }
          return;
        }
        reject(error);
      });
      server.once('listening', () => {
        const address = server.address();
        server.close(() => resolve(typeof address === 'object' && address ? address.port : port));
      });
      server.listen(port, '127.0.0.1');
    };

    tryPort(startPort);
  });
}

// RC1 Phase 0 — Security Remediation (Finding 2): no hardcoded fallback for
// SESSION_SECRET. This used to default to the well-known literal
// "dev-secret" whenever the env var was unset, which would let anyone
// forge a valid JWT for any deployment launched through this script. The
// backend's own Settings validation (backend/app/config.py) already fails
// fast if SESSION_SECRET is missing or empty, but we also check here so
// the failure is immediate and doesn't require a backend/.env file to be
// present for the message to be clear. For local development, generate a
// secret ONCE (so restarting the server doesn't invalidate active
// sessions) via:
//   python -c "import secrets; print(secrets.token_hex(32))"
// and put it in backend/.env as SESSION_SECRET=... (see backend/.env.example) —
// this script does not read backend/.env itself, so SESSION_SECRET must be
// present in this process's own environment (or backend/.env is picked up
// directly by the Python process via pydantic-settings).
const sessionSecretFromEnv = process.env.SESSION_SECRET;
const backendEnvFile = resolve(backendDir, '.env');
let backendHasOwnEnvFile = false;
try {
  const { existsSync } = await import('node:fs');
  backendHasOwnEnvFile = existsSync(backendEnvFile);
} catch {
  backendHasOwnEnvFile = false;
}
if (!sessionSecretFromEnv && !backendHasOwnEnvFile) {
  console.error(
    '\n[dev-backend] SESSION_SECRET is not set and backend/.env does not exist.\n' +
    '  Generate one with: python -c "import secrets; print(secrets.token_hex(32))"\n' +
    '  then either export SESSION_SECRET=<value> or copy backend/.env.example to\n' +
    '  backend/.env and fill it in. Refusing to start with no secret.\n'
  );
  process.exit(1);
}

const pythonExe = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const port = await getFreePort(Number(process.env.PORT || '8000'));
const child = spawn(pythonExe, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(port)], {
  cwd: backendDir,
  stdio: 'inherit',
  env: {
    ...process.env,
    PORT: String(port),
  },
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exit(code ?? 0);
  }
});
