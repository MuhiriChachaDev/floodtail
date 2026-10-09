"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  fetchAccessToken,
  refreshAccessToken,
  setAccessToken,
  getAccessToken,
} from "@/lib/api";

export type Role =
  | "Underwriter"
  | "Risk Analyst"
  | "Portfolio Manager"
  | "Approver";

export type User = {
  name: string;
  email: string;
  role: Role;
  initials: string;
};

type StoredSession = {
  user: User;
  lastActivityAt: number;
  idleTimeoutMinutes: number;
};

type AuthContextValue = {
  user: User | null;
  ready: boolean;
  /** Returns null on success, or an error message on failure. */
  login: (email: string, password: string, role?: Role) => Promise<string | null>;
  logout: () => void;
  setRole: (role: Role) => void;
  touchActivity: () => void;
};

const STORAGE_KEY = "floodtail.auth.v1";
const DEFAULT_IDLE_MINUTES = 10;
const ACTIVITY_EVENTS = [
  "mousemove",
  "mousedown",
  "keydown",
  "scroll",
  "touchstart",
  "click",
] as const;

const AuthContext = createContext<AuthContextValue | null>(null);

function initialsFrom(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

function readStoredSession(): StoredSession | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredSession | User;
    // Migrate old shape { name, email, ... } → session with activity stamp
    if ("user" in parsed && parsed.user) {
      return parsed as StoredSession;
    }
    if ("email" in parsed) {
      return {
        user: parsed as User,
        lastActivityAt: Date.now(),
        idleTimeoutMinutes: DEFAULT_IDLE_MINUTES,
      };
    }
  } catch {
    /* ignore */
  }
  return null;
}

function isExpired(session: StoredSession): boolean {
  const idleMs = (session.idleTimeoutMinutes || DEFAULT_IDLE_MINUTES) * 60_000;
  return Date.now() - session.lastActivityAt > idleMs;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const idleMinutesRef = useRef(DEFAULT_IDLE_MINUTES);
  const lastActivityRef = useRef(Date.now());
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearSession = useCallback(() => {
    setAccessToken(null);
    setUser(null);
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const persistSession = useCallback(
    (next: User | null, idleMinutes = idleMinutesRef.current) => {
      if (!next) {
        clearSession();
        return;
      }
      idleMinutesRef.current = idleMinutes;
      lastActivityRef.current = Date.now();
      setUser(next);
      const payload: StoredSession = {
        user: next,
        lastActivityAt: lastActivityRef.current,
        idleTimeoutMinutes: idleMinutes,
      };
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
      } catch {
        /* ignore */
      }
    },
    [clearSession],
  );

  const logout = useCallback(() => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
    clearSession();
  }, [clearSession]);

  const scheduleRefresh = useCallback(() => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    // Refresh JWT at half the idle window so active sessions keep working
    const ms = Math.max(30_000, (idleMinutesRef.current * 60_000) / 2);
    refreshTimerRef.current = setTimeout(async () => {
      if (!getAccessToken()) return;
      try {
        const token = await refreshAccessToken();
        setAccessToken(token.access_token);
        if (token.idle_timeout_minutes) {
          idleMinutesRef.current = token.idle_timeout_minutes;
        }
        scheduleRefresh();
      } catch {
        logout();
      }
    }, ms);
  }, [logout]);

  const touchActivity = useCallback(() => {
    if (!user) return;
    lastActivityRef.current = Date.now();
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as StoredSession;
      parsed.lastActivityAt = lastActivityRef.current;
      parsed.idleTimeoutMinutes = idleMinutesRef.current;
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(parsed));
    } catch {
      /* ignore */
    }
  }, [user]);

  useEffect(() => {
    const session = readStoredSession();
    if (session && !isExpired(session) && getAccessToken()) {
      idleMinutesRef.current = session.idleTimeoutMinutes || DEFAULT_IDLE_MINUTES;
      lastActivityRef.current = session.lastActivityAt;
      setUser(session.user);
      scheduleRefresh();
    } else {
      clearSession();
    }
    setReady(true);
  }, [clearSession, scheduleRefresh]);

  // Idle expiry watcher
  useEffect(() => {
    if (!user) return;

    const tick = () => {
      const idleMs = idleMinutesRef.current * 60_000;
      if (Date.now() - lastActivityRef.current > idleMs) {
        logout();
      }
    };
    const id = window.setInterval(tick, 15_000);
    tick();
    return () => window.clearInterval(id);
  }, [user, logout]);

  // Activity listeners (throttled)
  useEffect(() => {
    if (!user) return;
    let last = 0;
    const onActivity = () => {
      const now = Date.now();
      if (now - last < 1_000) return;
      last = now;
      touchActivity();
    };
    for (const ev of ACTIVITY_EVENTS) {
      window.addEventListener(ev, onActivity, { passive: true });
    }
    document.addEventListener("visibilitychange", onActivity);
    return () => {
      for (const ev of ACTIVITY_EVENTS) {
        window.removeEventListener(ev, onActivity);
      }
      document.removeEventListener("visibilitychange", onActivity);
    };
  }, [user, touchActivity]);

  const login = useCallback(
    async (
      email: string,
      password: string,
      role: Role = "Underwriter",
    ): Promise<string | null> => {
      const clean = email.trim();
      if (!clean || !password) return "Email and password are required.";
      try {
        const token = await fetchAccessToken({
          email: clean,
          password,
          role,
        });
        setAccessToken(token.access_token);
        const idle =
          token.idle_timeout_minutes ||
          token.expires_in_minutes ||
          DEFAULT_IDLE_MINUTES;
        const name =
          clean
            .split("@")[0]
            ?.replace(/[._-]+/g, " ")
            .replace(/\b\w/g, (c) => c.toUpperCase()) || "User";
        persistSession(
          {
            name,
            email: clean,
            role,
            initials: initialsFrom(name),
          },
          idle,
        );
        scheduleRefresh();
        return null;
      } catch (err) {
        setAccessToken(null);
        return err instanceof Error
          ? err.message
          : "Sign-in failed. Check credentials and that the API is running.";
      }
    },
    [persistSession, scheduleRefresh],
  );

  const setRole = useCallback(
    (role: Role) => {
      if (!user) return;
      persistSession({ ...user, role }, idleMinutesRef.current);
    },
    [persistSession, user],
  );

  const value = useMemo(
    () => ({ user, ready, login, logout, setRole, touchActivity }),
    [user, ready, login, logout, setRole, touchActivity],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
