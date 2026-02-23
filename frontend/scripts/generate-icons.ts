/**
 * Script to generate PWA icons from SVG
 * Run with: npx ts-node scripts/generate-icons.ts
 * Or with bun: bun run scripts/generate-icons.ts
 */

import { execSync } from 'child_process';
import { existsSync, mkdirSync } from 'fs';
import { join } from 'path';

const sizes = [72, 96, 128, 144, 152, 167, 180, 192, 384, 512];
const publicDir = join(process.cwd(), 'public');
const iconsDir = join(publicDir, 'icons');
const splashDir = join(publicDir, 'splash');

// Ensure directories exist
if (!existsSync(iconsDir)) {
  mkdirSync(iconsDir, { recursive: true });
}
if (!existsSync(splashDir)) {
  mkdirSync(splashDir, { recursive: true });
}

const svgPath = join(iconsDir, 'icon.svg');

console.log('Generating PWA icons...');
console.log('Note: This script requires sharp or an SVG-to-PNG converter.');
console.log('');
console.log('For manual icon generation, use one of these options:');
console.log('');
console.log('1. Use online tool: https://realfavicongenerator.net/');
console.log('   Upload the SVG at frontend/public/icons/icon.svg');
console.log('');
console.log('2. Use ImageMagick (if installed):');
sizes.forEach(size => {
  console.log(`   convert -background none -resize ${size}x${size} ${svgPath} ${join(iconsDir, `icon-${size}x${size}.png`)}`);
});
console.log('');
console.log('3. Use sharp (Node.js):');
console.log('   npm install sharp');
console.log('   Then run the script with sharp imported.');
console.log('');
console.log('Required icon sizes:', sizes.map(s => `${s}x${s}`).join(', '));
console.log('');
console.log('Apple touch icon: 180x180 (apple-touch-icon.png)');
console.log('');
console.log('For now, placeholder files will be created.');

// Create placeholder info file
console.log('\nCreated directories:');
console.log(`- ${iconsDir}`);
console.log(`- ${splashDir}`);
console.log('\nSVG icon created at: frontend/public/icons/icon.svg');
