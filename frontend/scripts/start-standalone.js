const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const root = path.resolve(__dirname, '..');
const standaloneRoot = path.join(root, '.next', 'standalone');

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function copyRecursive(source, destination) {
  if (!fs.existsSync(source)) return;
  ensureDir(destination);
  fs.cpSync(source, destination, { recursive: true, force: true });
}

function prepareStandalone() {
  const staticSource = path.join(root, '.next', 'static');
  const staticDestination = path.join(standaloneRoot, '.next', 'static');
  copyRecursive(staticSource, staticDestination);

  const publicSource = path.join(root, 'public');
  const publicDestination = path.join(standaloneRoot, 'public');
  copyRecursive(publicSource, publicDestination);
}

function startServer() {
  const serverPath = path.join(standaloneRoot, 'server.js');
  const child = spawn(process.execPath, [serverPath], {
    cwd: standaloneRoot,
    env: process.env,
    stdio: 'inherit',
  });

  child.on('exit', (code) => {
    process.exit(code ?? 0);
  });

  child.on('error', () => {
    process.exit(1);
  });
}

try {
  prepareStandalone();
  startServer();
} catch {
  process.exit(1);
}
