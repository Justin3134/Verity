/**
 * Base URL for browser-side calls to FastAPI.
 * When unset, use same-origin rewrites from next.config.ts (`/api/backend/*` → backend).
 */
export function getPublicBackendBase(): string {
  const u = process.env.NEXT_PUBLIC_BACKEND_URL?.trim();
  if (u) return u.replace(/\/$/, "");
  return "/api/backend";
}
