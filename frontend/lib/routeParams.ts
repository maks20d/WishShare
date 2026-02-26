export type RouteParamInput = string | string[] | null | undefined;

export function normalizeRouteParam(value: RouteParamInput): string | null {
  const raw = Array.isArray(value) ? value[0] : value;
  if (!raw) return null;

  let current = raw.trim();
  if (!current) return null;

  // Defensive decode: Next/router params can arrive percent-encoded.
  for (let i = 0; i < 2; i += 1) {
    if (!current.includes("%")) break;
    try {
      const decoded = decodeURIComponent(current);
      if (decoded === current) break;
      current = decoded;
    } catch {
      break;
    }
  }

  return current || null;
}

export function encodePathParam(value: RouteParamInput): string {
  const normalized = normalizeRouteParam(value);
  if (!normalized) return "";
  return encodeURIComponent(normalized);
}
