import { describe, expect, it } from "vitest";
import type { ReactElement } from "react";
import { render, screen } from "@testing-library/react";
import { ErrorBoundary } from "../ErrorBoundary";

function Boom(): ReactElement {
  throw new Error("boom");
  return <div />;
}

describe("ErrorBoundary", () => {
  it("renders fallback on error", () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );

    expect(screen.getByText("Что-то пошло не так")).toBeInTheDocument();
  });
});
