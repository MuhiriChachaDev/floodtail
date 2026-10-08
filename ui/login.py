"""FLOODTAIL — Kenya Re Branded Enterprise Authentication Screen.

Implements the pixel-perfect, responsive login page matching the official
Kenya Re Flood Risk Intelligence Platform design:
- Kenya Re dual-tone logo with 'YOUR REINSURANCE PARTNER' branding
- Nocturnal Kenya flood inundation map with glowing vector boundaries and node clusters
- 'KENYA FLOOD RISK INTELLIGENCE PLATFORM' typography
- 3 key value proposition badges (Flood Risk, Potential Losses, Better Decisions)
- Kenya Re angled brand stripes (White, Red, Blue)
- Frosted glassmorphism authentication card with cyan neon accent borders
- Interactive Email/Username + Password login, MFA simulation, and session management
"""

from __future__ import annotations

import streamlit as st


def get_login_css() -> str:
    """Return CSS styling for the Kenya Re login screen."""
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

/* Hide Streamlit default chrome when on login screen */
div[data-testid="stSidebarNav"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }
footer { visibility: hidden !important; }
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

:root {
    --kr-bg-dark: #040812;
    --kr-bg-surface: #0a1122;
    --kr-cyan: #00E5FF;
    --kr-cyan-glow: rgba(0, 229, 255, 0.4);
    --kr-cyan-subtle: rgba(0, 229, 255, 0.12);
    --kr-red: #E52320;
    --kr-blue: #0066CC;
    --kr-border: rgba(0, 229, 255, 0.25);
    --kr-text-primary: #FFFFFF;
    --kr-text-secondary: #94A3B8;
    --kr-text-muted: #64748B;
}

.kr-login-wrapper {
    min-height: 100vh;
    background: radial-gradient(circle at 30% 40%, #0d1a33 0%, #060c18 50%, #02050c 100%);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--kr-text-primary);
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 32px 64px 24px 64px;
    box-sizing: border-box;
}

/* Background animated flood grid */
.kr-bg-grid {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-image: 
        linear-gradient(to right, rgba(0, 229, 255, 0.03) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(0, 229, 255, 0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 1;
}

/* Kenya Map Overlay Illustration */
.kr-map-container {
    position: absolute;
    left: 28%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 650px;
    height: 650px;
    opacity: 0.85;
    pointer-events: none;
    z-index: 2;
}

.kr-content-grid {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 48px;
    align-items: center;
    position: relative;
    z-index: 10;
    flex: 1;
    margin-top: 16px;
    margin-bottom: 24px;
}

/* Left Hero Column */
.kr-hero-col {
    display: flex;
    flex-direction: column;
    justify-content: center;
    max-width: 640px;
}

.kr-header-brand {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 32px;
}

.kr-logo-title {
    font-size: 24px;
    font-weight: 800;
    letter-spacing: 0.5px;
    color: #FFFFFF;
    line-height: 1.1;
}

.kr-logo-sub {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2.2px;
    color: #CBD5E1;
    text-transform: uppercase;
}

.kr-platform-badge {
    font-size: 13px;
    font-weight: 500;
    color: #94A3B8;
    margin-bottom: 28px;
    letter-spacing: 0.3px;
}

.kr-main-headline {
    font-size: 40px;
    font-weight: 800;
    line-height: 1.15;
    letter-spacing: -0.5px;
    margin-bottom: 12px;
    text-transform: uppercase;
}

.kr-headline-white {
    color: #FFFFFF;
}

.kr-headline-cyan {
    color: var(--kr-cyan);
    text-shadow: 0 0 20px rgba(0, 229, 255, 0.4);
}

.kr-tagline {
    font-size: 15px;
    line-height: 1.5;
    color: #94A3B8;
    margin-bottom: 36px;
    max-width: 480px;
}

/* 3 Feature Pills */
.kr-features-list {
    display: flex;
    flex-direction: column;
    gap: 18px;
    margin-bottom: 40px;
}

.kr-feature-item {
    display: flex;
    align-items: center;
    gap: 16px;
}

.kr-feature-icon-circle {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: 1.5px solid var(--kr-cyan);
    background: rgba(0, 229, 255, 0.08);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 12px rgba(0, 229, 255, 0.25);
    flex-shrink: 0;
}

.kr-feature-icon-circle svg {
    width: 22px;
    height: 22px;
    fill: none;
    stroke: var(--kr-cyan);
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.kr-feature-text-title {
    font-size: 15px;
    font-weight: 700;
    color: #FFFFFF;
    margin-bottom: 2px;
}

.kr-feature-text-desc {
    font-size: 13px;
    color: #94A3B8;
}

/* Brand Stripes (Bottom Left) */
.kr-stripes-container {
    display: flex;
    gap: 8px;
    margin-top: auto;
}

.kr-stripe {
    height: 60px;
    width: 14px;
    transform: skewX(-24deg);
    border-radius: 2px;
}

.kr-stripe-white { background-color: #FFFFFF; }
.kr-stripe-red   { background-color: var(--kr-red); }
.kr-stripe-blue  { background-color: var(--kr-blue); }

/* Right Column — Authentication Card */
.kr-card-col {
    display: flex;
    justify-content: center;
}

.kr-login-card {
    width: 100%;
    max-width: 480px;
    background: rgba(10, 17, 34, 0.78);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid var(--kr-border);
    border-radius: 20px;
    padding: 40px 36px;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px rgba(0, 229, 255, 0.12);
    box-sizing: border-box;
}

.kr-card-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 28px;
}

.kr-shield-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    border: 1.5px solid var(--kr-cyan);
    background: rgba(0, 229, 255, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 16px rgba(0, 229, 255, 0.3);
    flex-shrink: 0;
}

.kr-card-title {
    font-size: 24px;
    font-weight: 700;
    color: #FFFFFF;
    margin-bottom: 4px;
}

.kr-card-subtitle {
    font-size: 13px;
    color: #94A3B8;
    line-height: 1.4;
}

/* Form Styles */
.kr-form-label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #E2E8F0;
    margin-bottom: 6px;
}

.kr-forgot-link {
    color: var(--kr-cyan);
    text-decoration: none;
    font-weight: 500;
    font-size: 13px;
    transition: color 0.2s ease;
}

.kr-forgot-link:hover {
    color: #67e8f9;
    text-decoration: underline;
}

/* Divider */
.kr-divider {
    display: flex;
    align-items: center;
    text-align: center;
    margin: 20px 0;
    color: #64748B;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
}

.kr-divider::before,
.kr-divider::after {
    content: '';
    flex: 1;
    border-bottom: 1px solid #1E293B;
}

.kr-divider:not(:empty)::before {
    margin-right: 16px;
}

.kr-divider:not(:empty)::after {
    margin-left: 16px;
}

/* Security badges footer inside card */
.kr-trust-footer {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-size: 11.5px;
    color: #64748B;
    margin-top: 20px;
}

.kr-trust-footer svg {
    width: 14px;
    height: 14px;
    fill: none;
    stroke: #64748B;
    stroke-width: 2;
}

/* Global Footer */
.kr-footer-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    color: #64748B;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    padding-top: 16px;
    position: relative;
    z-index: 10;
}

.kr-footer-links {
    display: flex;
    gap: 16px;
}

.kr-footer-links a {
    color: #64748B;
    text-decoration: none;
    transition: color 0.2s ease;
}

.kr-footer-links a:hover {
    color: var(--kr-cyan);
}

/* Streamlit button custom styles on login */
.stButton > button[kind="primary"], .kr-login-card button {
    background-color: var(--kr-cyan) !important;
    color: #040812 !important;
    font-weight: 800 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.4) !important;
    transition: all 0.2s ease !important;
    text-transform: uppercase !important;
}

.stButton > button[kind="primary"]:hover, .kr-login-card button:hover {
    background-color: #22d3ee !important;
    box-shadow: 0 0 28px rgba(0, 229, 255, 0.65) !important;
}

.stButton > button[kind="secondary"] {
    background-color: transparent !important;
    border: 1px solid var(--kr-border) !important;
    color: var(--kr-cyan) !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
}

.stButton > button[kind="secondary"]:hover {
    background-color: rgba(0, 229, 255, 0.08) !important;
    border-color: var(--kr-cyan) !important;
}

/* Responsive Media Queries */
@media (max-width: 1024px) {
    .kr-login-wrapper {
        padding: 24px 32px;
    }
    .kr-content-grid {
        grid-template-columns: 1fr;
        gap: 36px;
    }
    .kr-hero-col {
        max-width: 100%;
        text-align: center;
        align-items: center;
    }
    .kr-header-brand {
        justify-content: center;
    }
    .kr-main-headline {
        font-size: 32px;
    }
    .kr-map-container {
        display: none;
    }
    .kr-stripes-container {
        display: none;
    }
    .kr-footer-bar {
        flex-direction: column;
        gap: 8px;
        text-align: center;
    }
}

@media (max-width: 640px) {
    .kr-login-wrapper {
        padding: 16px;
    }
    .kr-login-card {
        padding: 28px 20px;
    }
    .kr-main-headline {
        font-size: 26px;
    }
    .kr-feature-item {
        text-align: left;
    }
}
</style>
"""


def render_login_page() -> None:
    """Render the full Kenya Re Flood Risk Intelligence Platform authentication page."""
    # Inject design system styling
    st.markdown(get_login_css(), unsafe_allow_html=True)

    # Kenya Re Logo SVG
    kenya_re_logo_svg = """
    <svg width="44" height="44" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <polygon points="12,12 36,12 18,88 12,88" fill="#E52320"/>
        <polygon points="26,12 66,12 50,44 34,44" fill="#FFFFFF"/>
        <polygon points="46,46 88,12 70,88 52,56" fill="#00E5FF"/>
        <polygon points="28,52 46,88 32,88 20,58" fill="#0066CC"/>
    </svg>
    """

    # Glowing Vector Map of Kenya SVG
    kenya_map_svg = """
    <svg viewBox="0 0 600 600" fill="none" xmlns="http://www.w3.org/2000/svg" class="kr-map-container">
        <!-- Ambient Radial Glows -->
        <circle cx="280" cy="360" r="160" fill="url(#radialGlow)" opacity="0.4"/>
        <circle cx="220" cy="420" r="70" fill="url(#cyanGlow)" opacity="0.6"/>
        <circle cx="360" cy="460" r="80" fill="url(#cyanGlow)" opacity="0.5"/>
        <circle cx="160" cy="380" r="60" fill="url(#cyanGlow)" opacity="0.5"/>

        <!-- Kenya Vector Boundary Contour -->
        <path d="M 210,140 
                 L 270,120 
                 L 380,170 
                 L 460,240 
                 L 450,340 
                 L 480,390 
                 L 420,440 
                 L 380,510 
                 L 340,540 
                 L 260,490 
                 L 200,470 
                 L 160,420 
                 L 140,360 
                 L 160,260 
                 L 180,200 Z" 
              stroke="#00E5FF" stroke-width="2.5" stroke-linejoin="round" 
              filter="url(#glowFilter)" fill="rgba(0, 229, 255, 0.03)" />

        <!-- River Networks (Tana & Athi Basins) -->
        <path d="M 230,360 Q 280,380 340,410 T 380,480" stroke="#00E5FF" stroke-width="1.8" opacity="0.85" stroke-dasharray="4,2"/>
        <path d="M 180,380 Q 230,370 280,360 T 330,330" stroke="#22D3EE" stroke-width="1.5" opacity="0.7"/>
        <path d="M 240,300 Q 290,320 360,370 T 430,420" stroke="#00E5FF" stroke-width="1.4" opacity="0.6"/>

        <!-- Major Peril Hotspots (Nairobi, Mombasa, Kisumu, Garissa) -->
        <g transform="translate(235, 385)">
            <circle cx="0" cy="0" r="8" fill="#00E5FF" filter="url(#nodeGlow)"/>
            <circle cx="0" cy="0" r="18" stroke="#00E5FF" stroke-width="1.5" opacity="0.7"/>
            <circle cx="0" cy="0" r="30" stroke="#00E5FF" stroke-width="0.75" opacity="0.3"/>
            <text x="14" y="4" fill="#FFFFFF" font-size="11" font-weight="700" font-family="Inter">Nairobi Basin</text>
        </g>

        <g transform="translate(365, 485)">
            <circle cx="0" cy="0" r="7" fill="#00E5FF" filter="url(#nodeGlow)"/>
            <circle cx="0" cy="0" r="14" stroke="#00E5FF" stroke-width="1.2" opacity="0.7"/>
            <text x="12" y="4" fill="#FFFFFF" font-size="10" font-weight="600" font-family="Inter">Mombasa Coast</text>
        </g>

        <g transform="translate(155, 380)">
            <circle cx="0" cy="0" r="7" fill="#00E5FF" filter="url(#nodeGlow)"/>
            <circle cx="0" cy="0" r="14" stroke="#00E5FF" stroke-width="1.2" opacity="0.7"/>
            <text x="-75" y="4" fill="#FFFFFF" font-size="10" font-weight="600" font-family="Inter">Lake Victoria</text>
        </g>

        <g transform="translate(340, 340)">
            <circle cx="0" cy="0" r="5" fill="#22D3EE" filter="url(#nodeGlow)"/>
            <circle cx="0" cy="0" r="10" stroke="#00E5FF" stroke-width="1" opacity="0.6"/>
            <text x="10" y="3" fill="#94A3B8" font-size="9" font-weight="500" font-family="Inter">Tana River</text>
        </g>

        <!-- SVG Gradients and Filters -->
        <defs>
            <radialGradient id="radialGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stop-color="#0066CC" stop-opacity="0.8"/>
                <stop offset="100%" stop-color="#0066CC" stop-opacity="0"/>
            </radialGradient>
            <radialGradient id="cyanGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stop-color="#00E5FF" stop-opacity="0.7"/>
                <stop offset="100%" stop-color="#00E5FF" stop-opacity="0"/>
            </radialGradient>
            <filter id="glowFilter" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feMerge>
                    <feMergeNode in="blur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
            <filter id="nodeGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                    <feMergeNode in="blur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
        </defs>
    </svg>
    """

    hero_html = f"""
    <div class="kr-bg-grid"></div>
    {kenya_map_svg}
    <div class="kr-content-grid">
        <!-- Left Column -->
        <div class="kr-hero-col">
            <div class="kr-header-brand">
                {kenya_re_logo_svg}
                <div>
                    <div class="kr-logo-title">KENYA <span style="color: #E52320;">RE</span></div>
                    <div class="kr-logo-sub">Your Reinsurance Partner</div>
                </div>
            </div>
            
            <div class="kr-platform-badge">Flood Risk Intelligence Platform</div>
            
            <div class="kr-main-headline">
                <span class="kr-headline-white">KENYA FLOOD</span><br/>
                <span class="kr-headline-cyan">RISK INTELLIGENCE PLATFORM</span>
            </div>
            
            <div class="kr-tagline">
                Understand flood risk. Model potential losses.<br/>
                Make better decisions.
            </div>
            
            <div class="kr-features-list">
                <div class="kr-feature-item">
                    <div class="kr-feature-icon-circle">
                        <svg viewBox="0 0 24 24"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"></path></svg>
                    </div>
                    <div>
                        <div class="kr-feature-text-title">Understand flood risk</div>
                        <div class="kr-feature-text-desc">See where and how floods can impact.</div>
                    </div>
                </div>
                
                <div class="kr-feature-item">
                    <div class="kr-feature-icon-circle">
                        <svg viewBox="0 0 24 24"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
                    </div>
                    <div>
                        <div class="kr-feature-text-title">Model potential losses</div>
                        <div class="kr-feature-text-desc">Turn data into actionable insights.</div>
                    </div>
                </div>
                
                <div class="kr-feature-item">
                    <div class="kr-feature-icon-circle">
                        <svg viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line><polyline points="4 8 10 2 16 8"></polyline></svg>
                    </div>
                    <div>
                        <div class="kr-feature-text-title">Make better decisions</div>
                        <div class="kr-feature-text-desc">With confidence and clarity.</div>
                    </div>
                </div>
            </div>
            
            <div class="kr-stripes-container">
                <div class="kr-stripe kr-stripe-white"></div>
                <div class="kr-stripe kr-stripe-red"></div>
                <div class="kr-stripe kr-stripe-blue"></div>
            </div>
        </div>
    """

    st.markdown(f'<div class="kr-login-wrapper">{hero_html}', unsafe_allow_html=True)

    # Right Column — Interactive Streamlit Glassmorphic Login Form
    left_spacer, right_form = st.columns([1.1, 0.9])

    with right_form:
        st.markdown(
            """
            <div class="kr-login-card">
                <div class="kr-card-header">
                    <div class="kr-shield-icon">
                        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#00E5FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                        </svg>
                    </div>
                    <div>
                        <div class="kr-card-title">Welcome Back</div>
                        <div class="kr-card-subtitle">Sign in to access the Kenya Flood CAT Risk Intelligence Platform.</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("kr_login_form"):
            st.markdown('<label class="kr-form-label">Email or Username</label>', unsafe_allow_html=True)
            email_input = st.text_input(
                "Email or Username",
                value="underwriter@kenyare.co.ke",
                placeholder="Enter your email or username",
                label_visibility="collapsed",
            )

            st.markdown('<label class="kr-form-label" style="margin-top: 14px;">Password</label>', unsafe_allow_html=True)
            password_input = st.text_input(
                "Password",
                value="••••••••••••",
                type="password",
                placeholder="Enter your password",
                label_visibility="collapsed",
            )

            col_rem, col_forgot = st.columns([1, 1])
            with col_rem:
                remember_me = st.checkbox("Remember me", value=True)
            with col_forgot:
                st.markdown('<div style="text-align: right; padding-top: 6px;"><a href="#" class="kr-forgot-link">Forgot password?</a></div>', unsafe_allow_html=True)

            submit_btn = st.form_submit_button(
                "SIGN IN ➔",
                use_container_width=True,
                type="primary",
            )

            if submit_btn:
                st.session_state["authenticated"] = True
                st.session_state["user_email"] = email_input or "underwriter@kenyare.co.ke"
                st.session_state["user_role"] = "Senior Reinsurance Underwriter"
                st.session_state["auth_method"] = "Standard Enterprise SSO"
                st.rerun()

        st.markdown('<div class="kr-divider">OR</div>', unsafe_allow_html=True)

        # Multi-Factor Authentication Option
        if st.button("🛡️ Sign in with Multi-Factor Authentication ➔", use_container_width=True, key="mfa_btn"):
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = "analyst.mfa@kenyare.co.ke"
            st.session_state["user_role"] = "Chief Actuary / Risk Auditor"
            st.session_state["auth_method"] = "FIDO2 / Hardware Token MFA"
            st.rerun()

        st.markdown(
            """
                <div class="kr-trust-footer">
                    <svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                    <span>Secure &bull; Audited &bull; Human Controlled</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Footer bar
    st.markdown(
        """
        </div>
        <div class="kr-footer-bar">
            <div>&copy; 2025 Kenya Reinsurance Corporation. All rights reserved.</div>
            <div class="kr-footer-links">
                <a href="#">Privacy</a>
                <span>&bull;</span>
                <a href="#">Security</a>
                <span>&bull;</span>
                <a href="#">Support</a>
                <span>&bull;</span>
                <span>Kenya Flood CAT Platform v1.0</span>
            </div>
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
