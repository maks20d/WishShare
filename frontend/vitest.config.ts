import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/*.{test,spec}.?(c|m)ts?(x)"],
    exclude: ["e2e/**", "node_modules/**", "coverage/**", ".next/**"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
    },
  },
});
