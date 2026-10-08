"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  Shield,
  ShieldCheck,
  Droplet,
  Network,
  BarChart3,
  Loader2,
  Check,
} from "lucide-react";
import styles from "./login.module.css";

function Logo() {
  return (
    <svg width="95" height="95" viewBox="0 0 100 100" aria-hidden>
      <path d="M8 18h12v62H8z" fill="#fff" />
      <path d="M26 56 70 6h16L42 56z" fill="#fff" />
      <path d="M42 56 86 6h8L50 60z" fill="#E11D2E" />
      <path d="M26 56 78 92H62L26 66z" fill="#E11D2E" />
      <path d="M30 92 48 70l18 22z" fill="#1D6FE0" />
    </svg>
  );
}

function KenyaOutline() {
  return (
    <svg className={styles.mapGlow} viewBox="0 0 280 360" fill="none" aria-hidden>
      <path
        className={styles.mapPath}
        d="M148 18c18 4 36 16 48 34 10 16 22 28 38 34 12 6 22 18 24 32 2 14 0 30-6 42 8 12 8 28 2 40-4 10-14 18-20 28-4 10-2 22 4 32-8 14-20 24-34 34-12 8-20 22-28 36-8 14-18 24-32 28-14 4-28-6-40-16-12-8-26-12-40-8-12 4-22 14-36 16-14 2-28-4-36-16-8-12-10-28-6-42-4-14-12-24-12-40 0-16 10-30 16-46 6-16 0-32 6-46 8-16 24-24 34-36C92 58 104 40 118 28c10-8 20-12 30-10z"
      />
      <circle className={styles.pulseDot} cx="92" cy="168" r="5" />
      <circle className={styles.pulseDot} cx="132" cy="200" r="6" />
      <circle className={styles.pulseDot} cx="78" cy="210" r="4" />
      <circle className={styles.pulseDot} cx="168" cy="268" r="4.5" />
      <circle className={styles.pulseDot} cx="118" cy="148" r="3.5" />
    </svg>
  );
}

const FEATURES = [
  { icon: Droplet, t: "Understand flood risk", s: "See where and how floods can impact." },
  { icon: Network, t: "Model potential losses", s: "Turn data into actionable insights." },
  { icon: BarChart3, t: "Make better decisions", s: "With confidence and clarity." },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("underwriter@kenyare.co.ke");
  const [password, setPassword] = useState("••••••••••••");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingText, setLoadingText] = useState("Loading Risk Intelligence Engine");
  const [toast, setToast] = useState({ show: false, message: "", type: "success" });
  const [bgFailed, setBgFailed] = useState(false);

  const triggerToast = (message, type = "success") => {
    setToast({ show: true, message, type });
    setTimeout(() => {
      setToast((prev) => ({ ...prev, show: false }));
    }, 4000);
  };

  const handleSignIn = async (e) => {
    if (e) e.preventDefault();
    if (!email.trim() || !password) {
      triggerToast("Please enter your email and password.", "error");
      return;
    }

    setIsLoading(true);
    setLoadingText("Authenticating Kenya Re Enterprise Credentials...");

    setTimeout(() => {
      setLoadingText("Loading Multi-Agent Catastrophe Pipeline & Portfolio Trace...");
    }, 800);

    setTimeout(() => {
      setIsLoading(false);
      triggerToast("✓ Welcome back. Loading your dashboard…", "success");
      setTimeout(() => {
        router.push("/dashboard");
      }, 700);
    }, 1700);
  };

  const handleMfaSignIn = () => {
    setIsLoading(true);
    setLoadingText("Verifying Hardware Token & Multi-Factor Auth...");
    setTimeout(() => {
      setIsLoading(false);
      triggerToast("MFA Authentication verified. Redirecting to Executive Overview...", "success");
      setTimeout(() => {
        router.push("/dashboard");
      }, 800);
    }, 1400);
  };

  const handleForgotPassword = (e) => {
    e.preventDefault();
    triggerToast("A secure password reset link has been dispatched to your corporate email.", "success");
  };

  return (
    <div className={styles.page}>
      <div className={styles.bgFallback} aria-hidden />
      {!bgFailed && (
        <img
          src="/login-bg.jpg"
          alt=""
          className={styles.bgPhoto}
          onError={() => setBgFailed(true)}
        />
      )}
      <div className={styles.bgOverlay} aria-hidden />
      <div className={styles.bgBottom} aria-hidden />

      <div className={styles.stripes} aria-hidden>
        <div className={`${styles.stripe} ${styles.stripeWhite}`} />
        <div className={`${styles.stripe} ${styles.stripeRed}`} />
        <div className={`${styles.stripe} ${styles.stripeBlue}`} />
      </div>

      {isLoading && (
        <div className={styles.loadingOverlay} role="status" aria-live="polite">
          <div className={styles.spinner} />
          <div>
            <div className={styles.loadingTitle}>Authenticating…</div>
            <div className={styles.loadingText}>{loadingText}</div>
          </div>
        </div>
      )}

      {toast.show && (
        <div
          className={`${styles.toast} ${toast.type === "success" ? styles.toastSuccess : styles.toastError}`}
          role="alert"
        >
          <div
            className={`${styles.toastIcon} ${toast.type === "success" ? styles.toastIconSuccess : styles.toastIconError}`}
          >
            {toast.type === "success" ? <Check size={16} /> : <span aria-hidden>×</span>}
          </div>
          <span className={styles.toastMsg}>{toast.message}</span>
        </div>
      )}

      <main className={styles.main}>
        <section className={styles.hero}>
          <KenyaOutline />

          <div className={styles.heroContent}>
          <div className={styles.brand}>
            <Logo />
            <div>
              <p className={styles.wordmark}>
                KENYA <span className={styles.re}>RE</span>
              </p>
              <p className={styles.tagline}>YOUR REINSURANCE PARTNER</p>
            </div>
          </div>
          <div className={styles.ruleWide} />
          <p className={styles.platform}>Flood Risk Intelligence Platform</p>
          <div className={styles.ruleShort} />

          <h1 className={styles.headline}>
            KENYA FLOOD
            <span className={styles.headlineAccent}>RISK INTELLIGENCE PLATFORM</span>
          </h1>
          <p className={styles.subtext}>
            Understand flood risk. Model potential losses.
            <br />
            Make better decisions.
          </p>

          <ul className={styles.features}>
            {FEATURES.map(({ icon: Icon, t, s }, i) => (
              <li
                key={t}
                className={styles.feature}
                style={{ animationDelay: `${0.15 * (i + 1)}s` }}
              >
                <span className={styles.featureIcon}>
                  <Icon size={28} />
                </span>
                <div>
                  <p className={styles.featureTitle}>{t}</p>
                  <p className={styles.featureSub}>{s}</p>
                </div>
              </li>
            ))}
          </ul>
          </div>
        </section>

        <section className={styles.card} role="region" aria-label="Sign in form">
          <div className={styles.cardHeader}>
            <span className={styles.shieldWrap}>
              <Shield size={64} strokeWidth={1.5} className={styles.shield} />
            </span>
            <div>
              <h2 className={styles.cardTitle}>Welcome Back</h2>
              <p className={styles.cardSubtitle}>
                Sign in to access the Kenya Flood CAT Risk Intelligence Platform.
              </p>
            </div>
          </div>

          <form onSubmit={handleSignIn} className={styles.form} noValidate>
            <label htmlFor="emailInput" className={styles.label}>
              Email or Username
            </label>
            <div className={styles.field}>
              <Mail className={styles.fieldIcon} size={24} />
              <input
                id="emailInput"
                name="email"
                type="text"
                className={styles.input}
                placeholder="Enter your email or username"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <label htmlFor="passwordInput" className={`${styles.label} ${styles.labelSpaced}`}>
              Password
            </label>
            <div className={styles.field}>
              <Lock className={styles.fieldIcon} size={24} />
              <input
                id="passwordInput"
                name="password"
                type={showPassword ? "text" : "password"}
                className={styles.input}
                placeholder="Enter your password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label="Show password"
                className={styles.eyeBtn}
              >
                {showPassword ? <EyeOff size={22} /> : <Eye size={22} />}
              </button>
            </div>

            <div className={styles.auxRow}>
              <label className={styles.checkLabel} htmlFor="rememberMe">
                <input
                  id="rememberMe"
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className={styles.srOnly}
                />
                <span className={`${styles.checkbox} ${rememberMe ? styles.checkboxOn : ""}`} aria-hidden>
                  {rememberMe && <Check size={14} color="#fff" strokeWidth={4} />}
                </span>
                Remember me
              </label>
              <button type="button" className={styles.forgot} onClick={handleForgotPassword}>
                Forgot password?
              </button>
            </div>

            <button type="submit" disabled={isLoading} className={styles.primaryBtn} id="signInBtn">
              {isLoading ? (
                <Loader2 className={styles.spin} />
              ) : (
                <>
                  SIGN IN <ArrowRight className={styles.arrow} />
                </>
              )}
            </button>

            <div className={styles.divider}>
              <span className={styles.dividerLine} />
              OR
              <span className={styles.dividerLine} />
            </div>

            <button
              type="button"
              className={styles.mfaBtn}
              onClick={handleMfaSignIn}
              disabled={isLoading}
            >
              <ShieldCheck size={26} />
              <span>Sign in with Multi-Factor Authentication</span>
              <ArrowRight size={22} />
            </button>

            <p className={styles.trust}>
              <Lock size={16} /> Secure
              <i className={styles.dot} /> Audited
              <i className={styles.dot} /> Human Controlled
            </p>
          </form>
        </section>
      </main>

      <footer className={styles.footer} role="contentinfo">
        <p>© 2025 Kenya Reinsurance Corporation. All rights reserved.</p>
        <nav className={styles.footerNav} aria-label="Footer navigation">
          <Link href="/privacy">Privacy</Link>
          <span className={styles.sep} />
          <Link href="/security">Security</Link>
          <span className={styles.sep} />
          <Link href="/support">Support</Link>
          <span className={styles.sep} />
          <span>Kenya Flood CAT Platform &nbsp; v1.0</span>
        </nav>
      </footer>
    </div>
  );
}
