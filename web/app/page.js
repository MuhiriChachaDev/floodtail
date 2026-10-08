'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import styles from './login.module.css';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('underwriter@kenyare.co.ke');
  const [password, setPassword] = useState('••••••••••••');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('Loading Risk Intelligence Engine');
  const [toast, setToast] = useState({ show: false, message: '', type: 'success' });

  const triggerToast = (message, type = 'success') => {
    setToast({ show: true, message, type });
    setTimeout(() => {
      setToast((prev) => ({ ...prev, show: false }));
    }, 4000);
  };

  const handleSignIn = async (e) => {
    if (e) e.preventDefault();
    if (!email.trim() || !password) {
      triggerToast('Please enter your email and password.', 'error');
      return;
    }

    setIsLoading(true);
    setLoadingText('Authenticating Kenya Re Enterprise Credentials...');

    setTimeout(() => {
      setLoadingText('Loading Multi-Agent Catastrophe Pipeline & Portfolio Trace...');
    }, 800);

    setTimeout(() => {
      setIsLoading(false);
      triggerToast('✓ Welcome back. Loading your dashboard…', 'success');
      setTimeout(() => {
        router.push('/dashboard');
      }, 700);
    }, 1700);
  };

  const handleMfaSignIn = () => {
    setIsLoading(true);
    setLoadingText('Verifying Hardware Token & Multi-Factor Auth...');
    setTimeout(() => {
      setIsLoading(false);
      triggerToast('MFA Authentication verified. Redirecting to Executive Overview...', 'success');
      setTimeout(() => {
        router.push('/dashboard');
      }, 800);
    }, 1400);
  };

  const handleForgotPassword = (e) => {
    e.preventDefault();
    triggerToast('A secure password reset link has been dispatched to your corporate email.', 'success');
  };

  return (
    <div className={styles.page}>
      {/* Background grid */}
      <div className="bg-grid" aria-hidden="true" />

      {/* Loading Overlay */}
      {isLoading && (
        <div className={styles.loadingOverlay} role="status" aria-live="polite">
          <div className={styles.spinner} />
          <div>
            <div className={styles.loadingTitle}>Authenticating…</div>
            <div className={styles.loadingText}>{loadingText}</div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toast.show && (
        <div
          className={`${styles.toast} ${toast.type === 'success' ? styles.toastSuccess : styles.toastError} animate-fade-in`}
          role="alert"
        >
          <div className={`${styles.toastIcon} ${toast.type === 'success' ? styles.toastIconSuccess : styles.toastIconError}`}>
            {toast.type === 'success' ? (
              <svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>
            ) : (
              <svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            )}
          </div>
          <span className={styles.toastMsg}>{toast.message}</span>
        </div>
      )}

      {/* Kenya Map Vector Overlay */}
      <svg className={styles.mapOverlay} viewBox="0 0 640 640" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <defs>
          <radialGradient id="rg1" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#0a5bcc" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#0a5bcc" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="rg2" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#00e5ff" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#00e5ff" stopOpacity="0" />
          </radialGradient>
          <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="nodeGlow" x="-80%" y="-80%" width="260%" height="260%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Ambient glows */}
        <circle cx="290" cy="390" r="175" fill="url(#rg1)" opacity="0.5" />
        <circle cx="230" cy="440" r="80" fill="url(#rg2)" opacity="0.55" />
        <circle cx="380" cy="490" r="90" fill="url(#rg2)" opacity="0.45" />
        <circle cx="160" cy="400" r="65" fill="url(#rg2)" opacity="0.45" />

        {/* Kenya boundary */}
        <path
          d="M220,145 L285,120 L400,175 L475,248 L462,355 L492,405 L428,455 L388,525 L345,555 L265,500 L205,480 L162,428 L145,368 L165,260 L188,200 Z"
          stroke="#00E5FF"
          strokeWidth="2.2"
          strokeLinejoin="round"
          fill="rgba(0,229,255,0.025)"
          filter="url(#glow)"
        />

        {/* River networks */}
        <path d="M238,372 Q290,396 352,424 T396,498" stroke="#00E5FF" strokeWidth="1.6" opacity="0.8" style={{ strokeDasharray: '6 3', animation: 'flow 2s linear infinite' }} />
        <path d="M185,398 Q240,386 295,370 T345,340" stroke="#22d3ee" strokeWidth="1.3" opacity="0.65" style={{ strokeDasharray: '6 3', animation: 'flow 2s linear infinite', animationDelay: '-1s' }} />
        <path d="M250,305 Q305,328 375,382 T445,435" stroke="#00b4ca" strokeWidth="1.2" opacity="0.5" style={{ strokeDasharray: '6 3', animation: 'flow 2s linear infinite', animationDelay: '-0.5s' }} />

        {/* Node: Nairobi Basin */}
        <g transform="translate(245,400)" style={{ animation: 'node-glow 2.8s ease-in-out infinite alternate' }} filter="url(#nodeGlow)">
          <circle r="9" fill="#00E5FF" />
          <circle style={{ animation: 'pulse 2.4s ease-out infinite', transformOrigin: 'center' }} r="9" stroke="#00E5FF" strokeWidth="1.8" fill="none" />
          <circle style={{ animation: 'pulse 2.4s ease-out infinite 0.8s', transformOrigin: 'center' }} r="9" stroke="#00E5FF" strokeWidth="1.2" fill="none" />
          <text x="14" y="4" fill="#fff" fontSize="10.5" fontWeight="700" fontFamily="Inter" paintOrder="stroke" stroke="#030912" strokeWidth="3">Nairobi Basin</text>
        </g>

        {/* Node: Mombasa Coast */}
        <g transform="translate(378,500)" style={{ animation: 'node-glow 2.8s ease-in-out infinite alternate 0.5s' }} filter="url(#nodeGlow)">
          <circle r="7" fill="#00E5FF" />
          <circle style={{ animation: 'pulse 2.4s ease-out infinite', transformOrigin: 'center' }} r="7" stroke="#00E5FF" strokeWidth="1.5" fill="none" />
          <text x="12" y="4" fill="#CBD5E1" fontSize="9.5" fontWeight="600" fontFamily="Inter" paintOrder="stroke" stroke="#030912" strokeWidth="3">Mombasa Coast</text>
        </g>

        {/* Node: Lake Victoria / Kisumu */}
        <g transform="translate(162,408)" style={{ animation: 'node-glow 2.8s ease-in-out infinite alternate 1s' }} filter="url(#nodeGlow)">
          <circle r="7" fill="#00E5FF" />
          <circle style={{ animation: 'pulse 2.4s ease-out infinite', transformOrigin: 'center' }} r="7" stroke="#00E5FF" strokeWidth="1.5" fill="none" />
          <text x="-82" y="4" fill="#CBD5E1" fontSize="9.5" fontWeight="600" fontFamily="Inter" paintOrder="stroke" stroke="#030912" strokeWidth="3">Lake Victoria</text>
        </g>

        {/* Node: Tana River */}
        <g transform="translate(352,348)" filter="url(#nodeGlow)">
          <circle r="5" fill="#22d3ee" />
          <text x="10" y="3" fill="#94A3B8" fontSize="9" fontWeight="500" fontFamily="Inter" paintOrder="stroke" stroke="#030912" strokeWidth="3">Tana River</text>
        </g>

        {/* Node: Garissa */}
        <g transform="translate(428,330)" filter="url(#nodeGlow)">
          <circle r="4.5" fill="#22d3ee" opacity="0.8" />
          <text x="9" y="3" fill="#94A3B8" fontSize="8.5" fontWeight="500" fontFamily="Inter" paintOrder="stroke" stroke="#030912" strokeWidth="3">Garissa</text>
        </g>
      </svg>

      {/* Main Content Wrapper */}
      <div className={styles.contentWrapper}>
        <main className={styles.mainGrid}>
          {/* Left Hero Column */}
          <div className={styles.hero}>
            {/* Kenya Re Brand */}
            <div className={styles.brand}>
              <div className={styles.brandLogo}>
                <svg width="48" height="48" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Kenya Re logo">
                  <polygon points="12,10 38,10 20,90 12,90" fill="#E52320" />
                  <polygon points="26,10 68,10 52,44 36,44" fill="#FFFFFF" />
                  <polygon points="48,48 90,10 72,90 54,58" fill="#00E5FF" />
                  <polygon points="30,54 48,90 34,90 18,58" fill="#0066CC" />
                </svg>
              </div>
              <div className={styles.brandTextGroup}>
                <div className={styles.brandName}>
                  KENYA <span className={styles.brandRed}>RE</span>
                </div>
                <div className={styles.brandTagline}>Your Reinsurance Partner</div>
              </div>
            </div>

            {/* Platform Badge */}
            <div className={styles.platformBadge}>Flood Risk Intelligence Platform</div>

            {/* Main Headline */}
            <h1 className={styles.headline}>
              <span className={styles.lineWhite}>Kenya Flood</span>
              <span className={styles.lineCyan}>Risk Intelligence Platform</span>
            </h1>

            {/* Tagline */}
            <p className={styles.subTagline}>
              Understand flood risk. Model potential losses.<br />
              Make better decisions.
            </p>

            {/* Features list */}
            <div className={styles.features}>
              <div className={styles.feature}>
                <div className={styles.featureIcon} aria-hidden="true">
                  <svg viewBox="0 0 24 24"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" /></svg>
                </div>
                <div>
                  <div className={styles.featureTitle}>Understand flood risk</div>
                  <div className={styles.featureDesc}>See where and how floods can impact.</div>
                </div>
              </div>

              <div className={styles.feature}>
                <div className={styles.featureIcon} aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <circle cx="18" cy="5" r="3" />
                    <circle cx="6" cy="12" r="3" />
                    <circle cx="18" cy="19" r="3" />
                    <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
                    <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
                  </svg>
                </div>
                <div>
                  <div className={styles.featureTitle}>Model potential losses</div>
                  <div className={styles.featureDesc}>Turn data into actionable insights.</div>
                </div>
              </div>

              <div className={styles.feature}>
                <div className={styles.featureIcon} aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <line x1="18" y1="20" x2="18" y2="10" />
                    <line x1="12" y1="20" x2="12" y2="4" />
                    <line x1="6" y1="20" x2="6" y2="14" />
                    <polyline points="4 8 10 2 16 8" />
                  </svg>
                </div>
                <div>
                  <div className={styles.featureTitle}>Make better decisions</div>
                  <div className={styles.featureDesc}>With confidence and clarity.</div>
                </div>
              </div>
            </div>

            {/* Brand Stripes */}
            <div className={styles.stripes} aria-hidden="true">
              <div className={`${styles.stripe} ${styles.stripeWhite}`} />
              <div className={`${styles.stripe} ${styles.stripeRed}`} />
              <div className={`${styles.stripe} ${styles.stripeBlue}`} />
            </div>
          </div>

          {/* Right Auth Card Column */}
          <div className={styles.cardCol}>
            <div className={styles.authCard} role="region" aria-label="Sign in form">
              {/* Header */}
              <div className={styles.cardHeader}>
                <div className={styles.shieldIcon} aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </div>
                <div>
                  <h2 className={styles.cardTitle}>Welcome Back</h2>
                  <p className={styles.cardSubtitle}>Sign in to access the Kenya Flood CAT Risk Intelligence Platform.</p>
                </div>
              </div>

              {/* Form */}
              <form onSubmit={handleSignIn} noValidate>
                {/* Email / Username */}
                <div className={styles.formGroup}>
                  <label className={styles.formLabel} htmlFor="emailInput">
                    Email or Username
                  </label>
                  <div className={styles.inputWrapper}>
                    <span className={styles.inputIcon} aria-hidden="true">
                      <svg viewBox="0 0 24 24">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                        <polyline points="22,6 12,13 2,6" />
                      </svg>
                    </span>
                    <input
                      type="text"
                      id="emailInput"
                      name="email"
                      className={styles.inputElement}
                      placeholder="Enter your email or username"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoComplete="username"
                      required
                    />
                  </div>
                </div>

                {/* Password */}
                <div className={styles.formGroup}>
                  <label className={styles.formLabel} htmlFor="passwordInput">
                    Password
                  </label>
                  <div className={styles.inputWrapper}>
                    <span className={styles.inputIcon} aria-hidden="true">
                      <svg viewBox="0 0 24 24">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                      </svg>
                    </span>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      id="passwordInput"
                      name="password"
                      className={styles.inputElement}
                      placeholder="Enter your password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      autoComplete="current-password"
                      required
                    />
                    <button
                      type="button"
                      className={styles.inputToggle}
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      <svg viewBox="0 0 24 24">
                        {showPassword ? (
                          <>
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                            <line x1="1" y1="1" x2="23" y2="23" />
                          </>
                        ) : (
                          <>
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </>
                        )}
                      </svg>
                    </button>
                  </div>
                </div>

                {/* Remember Me / Forgot Password */}
                <div className={styles.auxRow}>
                  <label className={styles.checkboxLabel} htmlFor="rememberMe">
                    <input
                      type="checkbox"
                      id="rememberMe"
                      className={styles.hiddenCheckbox}
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                    />
                    <span className={`${styles.checkboxBox} ${rememberMe ? styles.checkboxBoxChecked : styles.checkboxBoxUnchecked}`} aria-hidden="true">
                      {rememberMe && (
                        <svg viewBox="0 0 24 24">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      )}
                    </span>
                    Remember me
                  </label>
                  <button type="button" className={styles.forgotLink} onClick={handleForgotPassword}>
                    Forgot password?
                  </button>
                </div>

                {/* Sign In CTA */}
                <button type="submit" className={styles.btnPrimary} id="signInBtn" disabled={isLoading}>
                  Sign In
                  <svg viewBox="0 0 24 24">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                </button>
              </form>

              {/* Divider */}
              <div className={styles.divider}>OR</div>

              {/* MFA Button */}
              <button className={styles.btnMfa} type="button" onClick={handleMfaSignIn} disabled={isLoading}>
                <span className={styles.mfaLeft}>
                  <svg viewBox="0 0 24 24">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                  Sign in with Multi-Factor Authentication
                </span>
                <svg viewBox="0 0 24 24">
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </button>

              {/* Trust Footer */}
              <div className={styles.trustRow} aria-label="Security certifications">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                <span>Secure</span>
                <span className={styles.trustDot} aria-hidden="true" />
                <span>Audited</span>
                <span className={styles.trustDot} aria-hidden="true" />
                <span>Human Controlled</span>
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Site Footer */}
      <footer className={styles.siteFooter} role="contentinfo">
        <span>&copy; 2025 Kenya Reinsurance Corporation. All rights reserved.</span>
        <nav className={styles.footerLinks} aria-label="Footer navigation">
          <button type="button" onClick={() => triggerToast('Kenya Re Privacy & Data Residency Policy v2.4 (Nairobi Server Cluster)')}>Privacy</button>
          <span className={styles.footerSep}>|</span>
          <button type="button" onClick={() => triggerToast('SOC2 Type II & Kenya Insurance Regulatory Authority (IRA) Compliant')}>Security</button>
          <span className={styles.footerSep}>|</span>
          <button type="button" onClick={() => triggerToast('Kenya Re Underwriting Desk: risk@kenyare.co.ke | +254 20 272 6000')}>Support</button>
          <span className={styles.footerSep}>|</span>
          <span>Kenya Flood CAT Platform &nbsp;v1.0</span>
        </nav>
      </footer>
    </div>
  );
}
