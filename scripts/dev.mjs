import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import net from 'node:net';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const rootDir = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const webDir = resolve(rootDir, 'artifacts', 'web');

if (!existsSync(webDir)) {
  console.error(`Web workspace not found at ${webDir}`);
  process.exit(1);
}

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

const port = await getFreePort(Number(process.env.PORT || '5173'));
const child = spawn(process.platform === 'win32' ? 'cmd.exe' : 'pnpm', process.platform === 'win32'
  ? ['/d', '/s', '/c', 'pnpm run dev']
  : ['run', 'dev'], {
  cwd: webDir,
  stdio: 'inherit',
  shell: false,
  env: {
    ...process.env,
    PORT: String(port),
    BASE_PATH: process.env.BASE_PATH || '/',
  },
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exit(code ?? 0);
  }
});
