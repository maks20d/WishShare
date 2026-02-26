const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const tempDir = path.join(root, '.tmp');
const devDistDir = '.next-dev';

fs.mkdirSync(tempDir, { recursive: true });

process.env.TEMP = tempDir;
process.env.TMP = tempDir;
process.env.TMPDIR = tempDir;
process.env.NODE_ENV = 'development';
process.env.NEXT_DEV_DIST_DIR = devDistDir;

const majorNodeVersion = Number(process.versions.node.split('.')[0] || 0);
if (majorNodeVersion >= 24) {
  console.warn('[DEV] Node.js 24+ detected. If you see Windows spawn issues, use Node.js 22 LTS.');
}

try {
  fs.rmSync(path.join(root, devDistDir), { recursive: true, force: true });
} catch {}

async function start() {
  const host = process.env.HOSTNAME || '127.0.0.1';
  const port = Number(process.env.PORT || 3000);

  process.stdout.write(`TEMP_DIR=${tempDir}\n`);

  // WARNING: This uses an internal Next.js API (next/dist/server/lib/start-server)
  // which may change without notice in future Next.js versions.
  // If this breaks after a Next.js upgrade, check for API changes or
  // consider using `next start` command directly instead.
  const { startServer } = require('next/dist/server/lib/start-server');
  await startServer({
    dir: root,
    port,
    allowRetry: false,
    isDev: true,
    hostname: host,
  });
}

start().catch((error) => {
  console.error('[DEV] Failed to start development server:', error);
  process.exit(1);
});
