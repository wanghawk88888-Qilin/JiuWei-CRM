// ============================================================
// JiuWei CRM — stored-user helper (client-only)
// ============================================================

export interface StoredUser {
  id: number;
  username: string;
  real_name: string;
  role: string;
}

/** Read the logged-in user object persisted in localStorage (set at login). */
export function getStoredUser(): StoredUser | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = localStorage.getItem("user");
    if (!stored) return null;
    return JSON.parse(stored) as StoredUser;
  } catch {
    return null;
  }
}

/** True when the current user has the admin role. */
export function isAdminRole(): boolean {
  return getStoredUser()?.role === "admin";
}
