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

const pythonExe = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const port = await getFreePort(Number(process.env.PORT || '8000'));
const child = spawn(pythonExe, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(port)], {
  cwd: backendDir,
  stdio: 'inherit',
  env: {
    ...process.env,
    PORT: String(port),
    SESSION_SECRET: process.env.SESSION_SECRET || 'dev-secret',
  },
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exit(code ?? 0);
  }
});
