#!/usr/bin/env node
import sharp from "sharp";

const [source, pngTarget, webpTarget] = process.argv.slice(2);

if (!source || !pngTarget || !webpTarget) {
  console.error("Usage: node scripts/rasterize-svg.mjs <source.svg> <output.png> <output.webp>");
  process.exit(1);
}

const image = sharp(source, { density: 300 }).resize(2480, 3508, { fit: "fill" });
await image.png({ compressionLevel: 9, adaptiveFiltering: true }).toFile(pngTarget);
await sharp(pngTarget).webp({ quality: 90, effort: 6 }).toFile(webpTarget);
