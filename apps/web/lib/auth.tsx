"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

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

type AuthContextValue = {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string, role?: Role) => Promise<boolean>;
  logout: () => void;
  setRole: (role: Role) => void;
};

const STORAGE_KEY = "floodtail.auth.v1";

const AuthContext = createContext<AuthContextValue | null>(null);

function initialsFrom(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) setUser(JSON.parse(raw) as User);
    } catch {
      /* ignore */
    }
    setReady(true);
  }, []);

  const persist = useCallback((next: User | null) => {
    setUser(next);
    if (next) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    else window.localStorage.removeItem(STORAGE_KEY);
  }, []);

  const login = useCallback(
    async (email: string, _password: string, role: Role = "Underwriter") => {
      const clean = email.trim();
      if (!clean || !_password.trim()) return false;
      const name =
        clean
          .split("@")[0]
          ?.replace(/[._-]+/g, " ")
          .replace(/\b\w/g, (c) => c.toUpperCase()) || "Jane Doe";
      persist({
        name,
        email: clean,
        role,
        initials: initialsFrom(name),
      });
      return true;
    },
    [persist],
  );

  const logout = useCallback(() => persist(null), [persist]);

  const setRole = useCallback(
    (role: Role) => {
      if (!user) return;
      persist({ ...user, role });
    },
    [persist, user],
  );

  const value = useMemo(
    () => ({ user, ready, login, logout, setRole }),
    [user, ready, login, logout, setRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
