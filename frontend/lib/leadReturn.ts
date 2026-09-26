// Source-aware return routing for the lead detail page.
//
// The detail page can be reached from the dashboard "今日待跟进" queue, from
// the normal lead list, or from the `?followup=pending` filtered list. The
// origin is recorded in a whitelisted `from` query param so "back" and
// post-save navigation return to the right place — without ever accepting an
// arbitrary return URL and pushing it onto the router.

const RETURN_PATHS: Record<string, string> = {
  "dashboard-pending": "/dashboard",
  "pending-list": "/leads?followup=pending",
  list: "/leads",
};

const DEFAULT_RETURN_PATH = "/leads";

/** Map a whitelisted `from` source to its return path (defaults to /leads). */
export function resolveReturnPath(
  source: string | null | undefined,
): string {
  if (source && source in RETURN_PATHS) {
    return RETURN_PATHS[source];
  }
  return DEFAULT_RETURN_PATH;
}

/** True when the lead was opened from the dashboard pending queue. */
export function isDashboardPending(
  source: string | null | undefined,
): boolean {
  return source === "dashboard-pending";
}

/** Where to navigate after a successful followup save, or null to stay put.
 *
 * The dashboard queue and the pending-filtered list are "work-through" lists:
 * after saving, the counselor snaps back to keep moving through the queue. The
 * normal list (and any unknown / missing source) has no queue, so saving stays
 * on the detail page to show the new record in the timeline.
 */
export function resolvePostSaveRoute(
  source: string | null | undefined,
): string | null {
  if (source === "dashboard-pending") return "/dashboard";
  if (source === "pending-list") return "/leads?followup=pending";
  return null;
}
