import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { existsSync } from "node:fs";
import { describe, expect, it } from "vitest";

type ManifestEntry = {
  src: string;
};

type ManifestShape = {
  icons?: ManifestEntry[];
  screenshots?: ManifestEntry[];
  shortcuts?: Array<{ icons?: ManifestEntry[] }>;
};

function assetPath(src: string): string {
  return resolve(process.cwd(), "public", src.replace(/^\//, ""));
}

describe("manifest assets", () => {
  it("references only existing public files", () => {
    const raw = readFileSync(resolve(process.cwd(), "public", "manifest.json"), "utf-8");
    const manifest = JSON.parse(raw) as ManifestShape;

    const missing: string[] = [];

    for (const icon of manifest.icons ?? []) {
      if (!existsSync(assetPath(icon.src))) {
        missing.push(icon.src);
      }
    }

    for (const screenshot of manifest.screenshots ?? []) {
      if (!existsSync(assetPath(screenshot.src))) {
        missing.push(screenshot.src);
      }
    }

    for (const shortcut of manifest.shortcuts ?? []) {
      for (const icon of shortcut.icons ?? []) {
        if (!existsSync(assetPath(icon.src))) {
          missing.push(icon.src);
        }
      }
    }

    expect(missing).toEqual([]);
  });
});
