import { existsSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const rootDir = resolve(dirname(fileURLToPath(import.meta.url)), '..');

for (const name of ['package-lock.json', 'yarn.lock']) {
  const target = resolve(rootDir, name);
  if (existsSync(target)) {
    rmSync(target, { force: true });
  }
}

const agent = process.env.npm_config_user_agent || '';
if (!agent.startsWith('pnpm/')) {
  console.error('Use pnpm instead');
  process.exit(1);
}
