/**
 * Script to generate PWA icons from SVG using sharp
 * Run with: node scripts/generate-icons.mjs
 * 
 * First install sharp: npm install sharp --save-dev
 */

import sharp from 'sharp';
import { existsSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const publicDir = join(__dirname, '..', 'public');
const iconsDir = join(publicDir, 'icons');
const splashDir = join(publicDir, 'splash');

// Ensure directories exist
if (!existsSync(iconsDir)) {
  mkdirSync(iconsDir, { recursive: true });
}
if (!existsSync(splashDir)) {
  mkdirSync(splashDir, { recursive: true });
}

const sizes = [
  { name: 'icon-72x72.png', size: 72 },
  { name: 'icon-96x96.png', size: 96 },
  { name: 'icon-128x128.png', size: 128 },
  { name: 'icon-144x144.png', size: 144 },
  { name: 'icon-152x152.png', size: 152 },
  { name: 'icon-167x167.png', size: 167 },
  { name: 'icon-180x180.png', size: 180 },
  { name: 'icon-192x192.png', size: 192 },
  { name: 'icon-384x384.png', size: 384 },
  { name: 'icon-512x512.png', size: 512 },
];

const splashSizes = [
  { name: 'iphone.png', width: 750, height: 1334 },
  { name: 'iphone-x.png', width: 1125, height: 2436 },
  { name: 'iphone-xr.png', width: 828, height: 1792 },
  { name: 'iphone-xs-max.png', width: 1242, height: 2688 },
  { name: 'iphone-12.png', width: 1170, height: 2532 },
  { name: 'iphone-14-pro-max.png', width: 1290, height: 2796 },
  { name: 'ipad.png', width: 1536, height: 2048 },
  { name: 'ipad-pro-11.png', width: 1668, height: 2388 },
  { name: 'ipad-pro-12.png', width: 2048, height: 2732 },
];

const svgPath = join(iconsDir, 'icon.svg');

async function generateIcons() {
  console.log('Generating PWA icons...\n');

  // Generate regular icons
  for (const { name, size } of sizes) {
    const outputPath = join(iconsDir, name);
    try {
      await sharp(svgPath)
        .resize(size, size)
        .png()
        .toFile(outputPath);
      console.log(`✓ Generated ${name}`);
    } catch (error) {
      console.error(`✗ Failed to generate ${name}:`, error.message);
    }
  }

  // Generate apple-touch-icon
  const appleTouchIconPath = join(publicDir, 'apple-touch-icon.png');
  try {
    await sharp(svgPath)
      .resize(180, 180)
      .png()
      .toFile(appleTouchIconPath);
    console.log('✓ Generated apple-touch-icon.png');
  } catch (error) {
    console.error('✗ Failed to generate apple-touch-icon.png:', error.message);
  }

  // Generate splash screens
  console.log('\nGenerating splash screens...');
  for (const { name, width, height } of splashSizes) {
    const outputPath = join(splashDir, name);
    try {
      // Create splash screen with centered icon
      const iconSize = Math.min(width, height) * 0.4;
      const icon = await sharp(svgPath)
        .resize(Math.round(iconSize), Math.round(iconSize))
        .toBuffer();

      await sharp({
        create: {
          width,
          height,
          channels: 4,
          background: { r: 11, g: 11, b: 15, alpha: 1 }, // #0b0b0f
        }
      })
        .composite([{
          input: icon,
          gravity: 'center'
        }])
        .png()
        .toFile(outputPath);
      console.log(`✓ Generated ${name} (${width}x${height})`);
    } catch (error) {
      console.error(`✗ Failed to generate ${name}:`, error.message);
    }
  }

  console.log('\n✅ Icon generation complete!');
}

generateIcons().catch(console.error);
