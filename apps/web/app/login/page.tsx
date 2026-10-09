"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Lock, ShieldCheck } from "lucide-react";
import { FloodBackdrop } from "@/components/auth/FloodBackdrop";
import { KenyaReLogo } from "@/components/brand/KenyaReLogo";
import { useAuth, type Role } from "@/lib/auth";

export default function LoginPage() {
  const { user, ready, login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/home";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("Underwriter");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (ready && user) router.replace(next);
  }, [ready, user, router, next]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const errMsg = await login(email, password, role);
    setBusy(false);
    if (errMsg) {
      setError(errMsg);
      return;
    }
    router.replace(next);
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      <FloodBackdrop />

      <div className="relative z-10 grid w-full max-w-5xl gap-8 lg:grid-cols-2">
        <section className="hidden flex-col justify-center lg:flex">
          <KenyaReLogo variant="white" heightClass="h-12" priority />
          <p className="mt-5 text-xs font-semibold uppercase tracking-[0.22em] text-accent">
            FLOODTAIL
          </p>
          <h1 className="mt-3 font-display text-4xl font-semibold leading-tight text-white">
            Flood Risk Intelligence
          </h1>
          <p className="mt-4 max-w-md text-white/65">
            Sign in to see Nairobi flood risk for the Kenya Re book — from what
            we cover, to what a flood could cost, to who decides next.
          </p>
          <ul className="mt-8 space-y-3 text-sm text-white/60">
            <li>• Know what we have and where it is</li>
            <li>• Understand the flood and possible losses</li>
            <li>• Explore options — people approve the final call</li>
          </ul>
        </section>

        <section className="glass mx-auto w-full max-w-md rounded-2xl p-5 sm:rounded-3xl sm:p-8">
          <div className="mb-6 flex items-center gap-3">
            <KenyaReLogo variant="white" heightClass="h-9 sm:h-10" />
            <div className="min-w-0 border-l border-white/15 pl-3">
              <p className="font-display text-base font-semibold sm:text-lg">FLOODTAIL</p>
              <p className="text-xs text-white/45">Secure Kenya Re environment</p>
            </div>
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/60">
                Username / Email
              </label>
              <input
                className="input-field"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/60">
                Password
              </label>
              <input
                className="input-field"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/60">
                Role for this session
              </label>
              <select
                className="input-field"
                value={role}
                onChange={(e) => setRole(e.target.value as Role)}
              >
                <option>Underwriter</option>
                <option>Risk Analyst</option>
                <option>Portfolio Manager</option>
                <option>Approver</option>
              </select>
            </div>

            {error ? (
              <p className="text-sm text-rose-300">{error}</p>
            ) : (
              <p className="text-xs text-white/40">
                Sign in with your authorised credentials. Session ends on sign-out
                or after 10 minutes of inactivity. Any role may be selected when
                credentials match.
              </p>
            )}

            <button
              type="submit"
              disabled={busy}
              className="btn-primary w-full !rounded-xl"
            >
              <Lock className="h-4 w-4" />
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <div className="mt-6 flex items-center justify-between text-xs text-white/45">
            <button type="button" className="hover:text-accent">
              Forgot password?
            </button>
            <span className="inline-flex items-center gap-1">
              <ShieldCheck className="h-3.5 w-3.5 text-risk" />
              Kenya Re secure
            </span>
          </div>
        </section>
      </div>
    </main>
  );
}
