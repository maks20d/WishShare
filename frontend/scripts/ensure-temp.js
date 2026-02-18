const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const tempDir = path.join(root, ".tmp");
fs.mkdirSync(tempDir, { recursive: true });
process.stdout.write(`TEMP_DIR=${tempDir}`);
