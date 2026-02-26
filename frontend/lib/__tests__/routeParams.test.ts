import { describe, expect, it } from "vitest";

import { encodePathParam, normalizeRouteParam } from "../routeParams";

describe("routeParams helpers", () => {
  it("returns null for missing route params", () => {
    expect(normalizeRouteParam(undefined)).toBeNull();
    expect(normalizeRouteParam("")).toBeNull();
    expect(normalizeRouteParam([])).toBeNull();
  });

  it("normalizes array params and decodes encoded values", () => {
    expect(normalizeRouteParam(["wishlist-1"])).toBe("wishlist-1");
    expect(normalizeRouteParam("%D1%82%D0%B5%D1%81%D1%82")).toBe("тест");
    expect(normalizeRouteParam("%252Fencoded")).toBe("/encoded");
  });

  it("encodes normalized values for safe path usage", () => {
    expect(encodePathParam("тест список")).toBe("%D1%82%D0%B5%D1%81%D1%82%20%D1%81%D0%BF%D0%B8%D1%81%D0%BE%D0%BA");
    expect(encodePathParam("%D1%82%D0%B5%D1%81%D1%82")).toBe("%D1%82%D0%B5%D1%81%D1%82");
  });
});
