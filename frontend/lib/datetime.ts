// Centralized time formatting for the JiuWei CRM frontend.
//
// Two kinds of time values flow through the UI and must be treated differently:
//
//  1. System-generated timestamps (created_at / updated_at / followup created_at,
//     batch created_at, ...). The backend stores these as UTC and returns them as
//     "YYYY-MM-DD HH:MM:SS" (UTC wall clock). They must be shown to the user in
//     Beijing time (Asia/Shanghai, UTC+8).
//
//  2. next_followup_at — a user-selected *business* time (Beijing wall clock) from
//     <input type="datetime-local">. It is stored verbatim as the local value the
//     user picked (e.g. "2026-08-25T15:30") and must be shown exactly as entered,
//     with no ±8h shift.
//
// Pages must never render raw `item.created_at` / `followup.created_at` directly;
// route system times through formatSystemTime and next_followup_at through
// formatNextFollowup.

const BEIJING_OFFSET_MS = 8 * 60 * 60 * 1000;

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

/**
 * Parse a backend UTC datetime string and return a Date whose UTC components are
 * the corresponding Beijing wall-clock time. Returns null if the string is not a
 * recognizable "YYYY-MM-DD HH:MM:SS" value.
 */
function toBeijingDate(value: string): Date | null {
  let iso = value.trim();
  if (iso.endsWith("Z") || iso.endsWith("z")) {
    iso = iso.slice(0, -1);
  }
  iso = iso.replace("T", " ");
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})[ ](\d{2}):(\d{2}):(\d{2})$/);
  if (!m) return null;
  const [, y, mo, d, h, mi, s] = m;
  return new Date(Date.UTC(+y, +mo - 1, +d, +h, +mi, +s) + BEIJING_OFFSET_MS);
}

/**
 * Format a system-generated UTC timestamp as Beijing local "YYYY-MM-DD HH:MM:SS".
 * Returns "-" for empty values, and the original string when it cannot be parsed.
 */
export function formatSystemTime(value: string | null | undefined): string {
  if (!value) return "-";
  const bj = toBeijingDate(value);
  if (!bj) return value;
  return (
    `${bj.getUTCFullYear()}-${pad(bj.getUTCMonth() + 1)}-${pad(bj.getUTCDate())} ` +
    `${pad(bj.getUTCHours())}:${pad(bj.getUTCMinutes())}:${pad(bj.getUTCSeconds())}`
  );
}

/**
 * Format a user-selected next_followup_at without any timezone shift.
 *
 * Normalizes the ISO "T" separator to a space and trims to "YYYY-MM-DD HH:MM"
 * so the same business time the user picked is always redisplayed unchanged.
 */
export function formatNextFollowup(value: string | null | undefined): string {
  if (!value) return "-";
  const normalized = value.replace("T", " ").trim();
  return normalized.length >= 16 ? normalized.slice(0, 16) : normalized;
}
