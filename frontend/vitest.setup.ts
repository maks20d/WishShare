import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});

if (process.env.NODE_ENV === "test") {
  console.error = () => undefined;
  console.warn = () => undefined;
}
