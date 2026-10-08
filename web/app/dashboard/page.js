'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import styles from './dashboard.module.css';

// Dynamically load MapLibre GL 3D map of Nairobi (Client-side only)
const NairobiMap3D = dynamic(() => import('@/components/NairobiMap3D'), {
  ssr: false,
  loading: () => <div className="h-[420px] animate-pulse rounded-xl bg-slate-900" />,
});

// ===================================================================
// CONSTANTS & PIPELINE DEFINITION (Matching Image 2 Architecture)
// ===================================================================
const WORKFLOW_STEPS = [
  {
    id: 0,
    number: 'START',
    title: 'Upload / integrate exposure data',
    desc: 'Location, building/asset type, value, claims, treaty data; show data quality and confidence',
    domain: 'DATA',
    isAgentic: false,
    color: 'cyan',
    latency: '18ms',
  },
  {
    id: 1,
    number: '1',
    title: 'DATA QUALITY + GEOCODING',
    desc: 'Clean, validate, deduplicate, geocode, version and score uncertainty',
    domain: 'DATA',
    isAgentic: false,
    color: 'cyan',
    latency: '34ms',
  },
  {
    id: 2,
    number: '2',
    title: 'FLOOD HAZARD ENGINE',
    desc: 'Rainfall, rivers, terrain/DEM, drainage, fluvial, pluvial/urban, flash, coastal; flood extent, depth, duration and velocity',
    domain: 'RISK',
    isAgentic: false,
    color: 'cyan',
    latency: '78ms',
  },
  {
    id: 3,
    number: '3',
    title: 'STOCHASTIC EVENT ENGINE',
    desc: 'Thousands of plausible flood events, probabilities, return periods, scenario and stress events',
    domain: 'RISK',
    isAgentic: false,
    color: 'cyan',
    latency: '112ms',
  },
  {
    id: 4,
    number: '4',
    title: 'EXPOSURE + ACCUMULATION',
    desc: 'Which Kenya Re risks are affected? Exposure by county/city/basin/cedant/treaty; concentration hotspots',
    domain: 'DATA',
    isAgentic: false,
    color: 'cyan',
    latency: '45ms',
  },
  {
    id: 5,
    number: '5',
    title: 'VULNERABILITY + LOSS',
    desc: 'Depth-to-damage by asset type; ground-up loss → insured loss; uncertainty bands; Kenya-calibrated vulnerability',
    domain: 'RISK',
    isAgentic: false,
    color: 'cyan',
    latency: '52ms',
  },
  {
    id: 6,
    number: '6',
    title: 'REINSURANCE FINANCIAL ENGINE',
    desc: 'Treaty terms, retention, attachment, limits, reinstatement; Kenya Re gross loss → retrocession → Kenya Re net loss',
    domain: 'FINANCE',
    isAgentic: false,
    color: 'cyan',
    latency: '61ms',
  },
  {
    id: 7,
    number: '7',
    title: 'RISK METRICS',
    desc: 'AAL, PML, TVaR, EP/OEP/AEP, return-period losses, accumulation and stress testing',
    domain: 'RISK',
    isAgentic: false,
    color: 'cyan',
    latency: '84ms',
  },
  {
    id: 8,
    number: '8',
    title: 'CAPITAL + DECISION INTELLIGENCE',
    desc: 'Capital/risk appetite interface, pricing and underwriting inputs, portfolio decisions, pool/retrocession scenarios',
    domain: 'FINANCE',
    isAgentic: false,
    color: 'cyan',
    latency: '39ms',
  },
  {
    id: 9,
    number: '9',
    title: 'AGENTIC AI + LLM',
    desc: 'Reads and investigates, runs approved scenarios through tools, explains results, monitors anomalies, drafts recommendations; NEVER calculates CAT numbers itself',
    domain: 'DECISIONS',
    isAgentic: true,
    color: 'purple',
    latency: '142ms',
  },
  {
    id: 10,
    number: '10',
    title: 'HUMAN OVERSIGHT',
    desc: 'Model approval, material underwriting, capital/risk appetite, retrocession, major model changes and exceptional events; approve / override / escalate',
    domain: 'DECISIONS',
    isAgentic: false,
    color: 'purple',
    latency: 'Human Gate',
  },
  {
    id: 11,
    number: 'FINAL',
    title: 'FINAL OUTPUT',
    desc: 'Approved risk view, pricing/underwriting recommendation, capital/retrocession view, audit trail',
    domain: 'DECISIONS',
    isAgentic: false,
    color: 'cyan',
    latency: 'Verified',
  },
];

const HOTSPOTS_DATA = [
  {
    id: 'nairobi',
    name: 'Nairobi Metropolitan & Industrial Area',
    region: 'Nairobi Basin (Pluvial / Urban)',
    depth: '2.45 m',
    tiv: 'KES 142.5M',
    insuredBuildings: 84,
    uninsuredBuildings: 310,
    severity: 'CRITICAL',
    rec: 'Apply 15% Sub-limit & Zone Inundation Deductible',
  },
  {
    id: 'kisumu',
    name: 'Kisumu Lake Victoria Basin & Nyando River',
    region: 'Lake Victoria Basin (Riverine / Lacustrine)',
    depth: '1.80 m',
    tiv: 'KES 68.2M',
    insuredBuildings: 42,
    uninsuredBuildings: 180,
    severity: 'ELEVATED',
    rec: 'Monitor Riverine Crests; Surcharge Agricultural Risks',
  },
  {
    id: 'mombasa',
    name: 'Mombasa Port & Kilindini Coastal Harbor',
    region: 'Coastal Strip (Tidal Surge / Pluvial)',
    depth: '1.25 m',
    tiv: 'KES 69.3M',
    insuredBuildings: 71,
    uninsuredBuildings: 125,
    severity: 'MODERATE',
    rec: 'Enforce Seawall Buffer & Cargo Elevation Endorsement',
  },
];

export default function DashboardPage() {
  const router = useRouter();

  // Navigation & View States
  const [activeNav, setActiveNav] = useState('home'); // 'home' | 'about'
  const [selectedRole, setSelectedRole] = useState('Underwriter');
  const [isRoleDropdownOpen, setIsRoleDropdownOpen] = useState(false);

  // Workflow / Command Center Drawer State (Image 2)
  const [isWorkflowOpen, setIsWorkflowOpen] = useState(false);
  const [selectedWorkflowStep, setSelectedWorkflowStep] = useState(WORKFLOW_STEPS[0]);
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [activeRunningStep, setActiveRunningStep] = useState(null);

  // Map Interactive States
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isSimPlaying, setIsSimPlaying] = useState(false);
  const [rainfallMm, setRainfallMm] = useState(85);
  const [mapFilter, setMapFilter] = useState('insured'); // 'insured' | 'all'
  const [selectedHotspot, setSelectedHotspot] = useState(null);

  // Domain Drawer & Cross-Cutting Modals
  const [activeDomainDrawer, setActiveDomainDrawer] = useState(null); // 'DATA' | 'RISK MODELLING' | 'FINANCE' | 'DECISIONS'
  const [crossCuttingModal, setCrossCuttingModal] = useState(null);
  const [showLearningDetail, setShowLearningDetail] = useState(null);

  // Simulation timer for rainfall playback
  useEffect(() => {
    let timer;
    if (isSimPlaying) {
      timer = setInterval(() => {
        setRainfallMm((prev) => {
          if (prev >= 180) return 30;
          return prev + 15;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isSimPlaying]);

  // Execute full 11-stage pipeline sequentially
  const handleRunPipelineSimulation = () => {
    setIsPipelineRunning(true);
    let current = 0;
    const interval = setInterval(() => {
      setActiveRunningStep(current);
      setSelectedWorkflowStep(WORKFLOW_STEPS[current]);
      current++;
      if (current >= WORKFLOW_STEPS.length) {
        clearInterval(interval);
        setTimeout(() => {
          setIsPipelineRunning(false);
          setActiveRunningStep(null);
        }, 800);
      }
    }, 450);
  };

  // Dynamic calculations for KPIs based on rainfall
  const dynamicTiv = 'KES 280.0M';
  const dynamicAal = `KES ${(120 + (rainfallMm / 200) * 18.5).toFixed(2)}M`;
  const dynamicTvar = `KES ${(215 + (rainfallMm / 200) * 26.2).toFixed(1)}M`;
  const dynamicExposures = 197;

  return (
    <div className={styles.dashboardContainer}>
      {/* ===================================================================
          1. TOP NAVBAR
          =================================================================== */}
      <header className={styles.topNav}>
        <div className={styles.navLeft}>
          <div className={styles.logoWrapper} onClick={() => setActiveNav('home')}>
            <svg className={styles.logoSvg} viewBox="0 0 100 100" fill="none">
              <polygon points="12,12 38,12 20,88 12,88" fill="#E52320" />
              <polygon points="26,12 68,12 52,44 36,44" fill="#FFFFFF" />
              <polygon points="48,48 90,12 72,88 54,58" fill="#00E5FF" />
              <polygon points="30,54 48,88 34,88 18,58" fill="#0066CC" />
            </svg>
            <div className={styles.brandText}>
              <span className={styles.brandTitle}>KENYA RE</span>
              <span className={styles.brandTagline}>STRENGTH · INSIGHT · TOGETHER</span>
            </div>
          </div>

          <div className={styles.navDivider} />
          <span className={styles.platformTitle}>Flood Risk Intelligence Platform</span>
        </div>

        {/* Center Nav Links */}
        <nav className={styles.navCenter}>
          <button
            type="button"
            className={`${styles.navBtn} ${activeNav === 'home' ? styles.navBtnActive : ''}`}
            onClick={() => {
              setActiveNav('home');
              setIsWorkflowOpen(false);
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            Home
          </button>

          <span className={styles.navSep}>|</span>

          <button
            type="button"
            className={`${styles.navBtn} ${activeNav === 'about' ? styles.navBtnActive : ''}`}
            onClick={() => setActiveNav('about')}
          >
            About
          </button>
        </nav>

        {/* Right Controls */}
        <div className={styles.navRight}>
          {/* Persona / Role Selector */}
          <div style={{ position: 'relative' }}>
            <button
              type="button"
              className={styles.roleSelectBtn}
              onClick={() => setIsRoleDropdownOpen(!isRoleDropdownOpen)}
            >
              <svg viewBox="0 0 24 24">
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
              </svg>
              <span>{selectedRole}</span>
              <span style={{ fontSize: '10px', opacity: 0.8 }}>▼</span>
            </button>

            {isRoleDropdownOpen && (
              <div
                style={{
                  position: 'absolute',
                  top: '100%',
                  right: 0,
                  marginTop: '8px',
                  background: '#07152b',
                  border: '1px solid rgba(0, 229, 255, 0.3)',
                  borderRadius: '10px',
                  boxShadow: '0 10px 30px rgba(0,0,0,0.7)',
                  zIndex: 110,
                  width: '160px',
                  overflow: 'hidden',
                }}
              >
                {['Underwriter', 'Chief Actuary', 'Risk Officer', 'Audit Executive'].map((role) => (
                  <button
                    key={role}
                    type="button"
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      background: 'none',
                      border: 'none',
                      color: selectedRole === role ? '#00E5FF' : '#CBD5E1',
                      textAlign: 'left',
                      fontSize: '13px',
                      fontWeight: selectedRole === role ? '700' : '500',
                      cursor: 'pointer',
                      borderBottom: '1px solid rgba(255,255,255,0.05)',
                    }}
                    onClick={() => {
                      setSelectedRole(role);
                      setIsRoleDropdownOpen(false);
                    }}
                  >
                    {role}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Run / View Portfolio Button */}
          <button
            type="button"
            className={styles.runPortfolioBtn}
            onClick={() => setIsWorkflowOpen(true)}
          >
            <svg viewBox="0 0 24 24">
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
            <span>Run / View Portfolio</span>
          </button>

          {/* User Profile */}
          <div className={styles.userBadge} onClick={() => router.push('/')} title="Sign Out">
            <div className={styles.avatarCircle}>JD</div>
            <div className={styles.userMeta}>
              <span className={styles.userName}>Jane Doe</span>
              <span className={styles.userRole}>Underwriter</span>
            </div>
            <span style={{ fontSize: '10px', color: '#94A3B8' }}>▼</span>
          </div>
        </div>
      </header>

      {/* ===================================================================
          2. MAIN VIEW BODY
          =================================================================== */}
      <main className={styles.mainContent}>
        {/* ===================================================================
            HERO CARD (with Nairobi twilight photo background & overlay)
            =================================================================== */}
        <section className={styles.heroCard}>
          <div className={styles.heroBgImage} />
          <div className={styles.heroOverlay} />

          {/* Hero Left */}
          <div className={styles.heroContentLeft}>
            <div className={styles.heroTagline}>SMARTER INSIGHTS. STRONGER DECISIONS.</div>
            <h1 className={styles.heroHeading}>
              KENYA RE
              <span className={styles.heroHeadingHighlight}>Flood Risk Intelligence Platform</span>
            </h1>
            <p className={styles.heroSubtext}>
              AI-powered insights for flood catastrophe risk, pricing and reinsurance decisions — all in one platform.
            </p>
            <button
              type="button"
              className={styles.commandCenterBtn}
              onClick={() => setIsWorkflowOpen(true)}
            >
              <span>Open Command Center</span>
              <svg viewBox="0 0 24 24">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </div>

          {/* Hero Right: Glassmorphism Card */}
          <div className={styles.heroContentRight}>
            <div className={styles.heroGlassCard}>
              <div className={styles.glassCardTitle}>Real risk. Real data. Real decisions.</div>
              <p className={styles.glassCardText}>
                From flood events and hazard modelling to pricing and reinsurance, FLOODTAIL gives you the clarity to manage risk and unlock opportunity.
              </p>
            </div>

            <div className={styles.heroLocation}>
              <span>📍</span>
              <span>Nairobi, Kenya</span>
            </div>
          </div>
        </section>

        {/* ===================================================================
            FOUR DOMAIN CARDS (DATA, RISK MODELLING, FINANCE, DECISIONS)
            =================================================================== */}
        <section className={styles.domainCardsRow} aria-label="Core Catastrophe Domains">
          {/* Card 1: DATA */}
          <div
            className={`${styles.domainCard} ${styles.cardData}`}
            onClick={() => setActiveDomainDrawer('DATA')}
          >
            {/* Background Watermark Contour */}
            <svg className={styles.domainWatermark} viewBox="0 0 200 150" fill="none">
              <path d="M10,80 Q50,20 120,60 T190,110" stroke="#3b82f6" strokeWidth="1.5" />
              <path d="M10,110 Q70,50 140,90 T200,140" stroke="#3b82f6" strokeWidth="1" />
            </svg>

            <div className={styles.domainCardHeader}>
              <div className={styles.domainIcon}>
                <svg viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2">
                  <ellipse cx="12" cy="5" rx="9" ry="3" />
                  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                </svg>
              </div>
              <div className={styles.domainArrowBtn}>
                <svg viewBox="0 0 24 24">
                  <line x1="7" y1="17" x2="17" y2="7" />
                  <polyline points="7 7 17 7 17 17" />
                </svg>
              </div>
            </div>

            <div className={styles.domainCardTitle}>DATA</div>
            <div className={styles.domainCardSubtitle}>Trusted data. Better decisions.</div>

            <ul className={styles.domainBulletList}>
              <li className={styles.domainBulletItem}>
                <span className={styles.bulletDot} />
                <span>Data Intake</span>
              </li>
              <li className={styles.domainBulletItem}>
                <span className={styles.bulletDot} />
                <span>Data Quality & Location</span>
              </li>
              <li className={styles.domainBulletItem}>
                <span className={styles.bulletDot} />
                <span>Portfolio & Exposure</span>
              </li>
            </ul>
          </div>

          {/* Card 2: RISK MODELLING */}
          <div
            className={`${styles.domainCard} ${styles.cardRisk}`}
            onClick={() => setActiveDomainDrawer('RISK MODELLING')}
          >
            {/* Background Watermark Contour */}
            <svg className={styles.domainWatermark} viewBox="0 0 200 150" fill="none">
              <circle cx="150" cy="100" r="40" stroke="#00E5FF" strokeWidth="1.2" />
              <circle cx="150" cy="100" r="65" stroke="#00E5FF" strokeWidth="0.8" />
            </svg>

            <div className={styles.domainCardHeader}>
              <div className={styles.domainIcon}>
                <svg viewBox="0 0 24 24" fill="none" stroke="#00E5FF" strokeWidth="2">
                  <circle cx="18" cy="5" r="3" />
                  <circle cx="6" cy="12" r="3" />
                  <circle cx="18" cy="19" r="3" />
                  <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
                  <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
                </svg>
              </div>
              <div className={styles.domainArrowBtn}>
                <svg viewBox="0 0 24 24">
                  <line x1="7" y1="17" x2="17" y2="7" />
                  <polyline points="7 7 17 7 17 17" />
                </svg>
              </div>
            </div>

            <div className={styles.domainCardTitle}>RISK MODELLING</div>
            <div className={styles.domainCardSubtitle}>From hazard to loss.</div>

            <ul className={styles.domainBulletList}>
              <li className={styles.domainBulletItem}>
                <span className={styles.bulletDot} />
                <span>Flood Hazard</span>
              </li>
              <li className={styles.domainBulletItem}>
                <span className={styles.bulletDot} />
                <span>Event Simulation</span>
              </li>
              <li className={styles.domainBulletItem}>
                <span className={styles.bulletDot} />
                <span>Loss Modelling</span>
              </li>
              <li className={styles.domainBulletItem}>
                <span className={styles.bulletDot} />
                <span>Risk Analytics</span>
              </li>
            </ul>
          </div>

          {/* Card 3: FINANCE */}
          <div
            className={`${styles.domainCard} ${styles.cardFinance}`}
            onClick={() => setActiveDomainDrawer('FINANCE')}
          >
            {/* Background Watermark Trendline */}
            <svg className={styles.domainWatermark} viewBox="0 0 200 150" fill="none">
              <path d="M10,130 L60,110 L100,120 L150,70 L190,40" stroke="#f59e0b" strokeWidth="1.8" />
            </svg>

            <div className={styles.domainCardHeader}>
              <div className={styles.domainIcon}>
                <svg viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2">
                  <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                </svg>
              </div>
              <div className={styles.domainArrowBtn}>
                <svg viewBox="0 0 24 24">
                  <line x1="7" y1="17" x2="17" y2="7" />
                  <polyline points="7 7 17 7 17 17" />
                </svg>
              </div>
            </div>

            <div className={styles.domainCardTitle}>FINANCE</div>
            <div className={styles.domainCardSubtitle}>Understand the financial impact.</div>

            <ul className={styles.domainBulletList}>
              <li className={styles.domainBulletItem}>
                <span className={styles.bulletDot} />
                <span>Reinsurance</span>
              </li>
              <li className={styles.domainBulletItem}>
                <span className={styles.bulletDot} />
                <span>Capital & Portfolio</span>
              </li>
            </ul>
          </div>

          {/* Card 4: DECISIONS */}
          <div
            className={`${styles.domainCard} ${styles.cardDecisions}`}
            onClick={() => setActiveDomainDrawer('DECISIONS')}
          >
            {/* Background Watermark Neural Dots */}
            <svg className={styles.domainWatermark} viewBox="0 0 200 150" fill="none">
              <circle cx="160" cy="70" r="2" fill="#8b5cf6" />
              <circle cx="175" cy="85" r="2" fill="#8b5cf6" />
              <circle cx="145" cy="95" r="2" fill="#8b5cf6" />
              <circle cx="180" cy="110" r="2" fill="#8b5cf6" />
              <line x1="160" y1="70" x2="175" y2="85" stroke="#8b5cf6" strokeWidth="0.8" opacity="0.4" />
              <line x1="175" y1="85" x2="145" y2="95" stroke="#8b5cf6" strokeWidth="0.8" opacity="0.4" />
            </svg>

            <div className={styles.domainCardHeader}>
              <div className={styles.domainIcon}>
                <svg viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2">
                  <rect x="4" y="4" width="16" height="16" rx="2" />
                  <circle cx="9" cy="9" r="2" />
                  <path d="M15 9h.01M9 15h.01M15 15h.01" />
                </svg>
              </div>
              <div className={styles.domainArrowBtn}>
                <svg viewBox="0 0 24 24">
                  <line x1="7" y1="17" x2="17" y2="7" />
                  <polyline points="7 7 17 7 17 17" />
                </svg>
              </div>
            </div>

            <div className={styles.domainCardTitle}>DECISIONS</div>
            <div className={styles.domainCardSubtitle}>Smarter with human judgment.</div>

            <ul className={styles.domainBulletList}>
              <li className={styles.domainBulletItem}>
                <span className={styles.bulletDot} />
                <span>AI Intelligence</span>
              </li>
              <li className={styles.domainBulletItem}>
                <span className={styles.bulletDot} />
                <span>Human Decisions</span>
              </li>
              <li className={styles.domainBulletItem}>
                <span className={styles.bulletDot} />
                <span>Decision Output</span>
              </li>
            </ul>
          </div>
        </section>

        {/* ===================================================================
            SPLIT SECTION: FLOOD RISK MAP (LEFT) & PORTFOLIO/LEARNING (RIGHT)
            =================================================================== */}
        <section className={styles.splitSection}>
          {/* ---------------------------------------------------------------
              FLOOD RISK MAP (LEFT PANEL)
              --------------------------------------------------------------- */}
          <div className={styles.mapCard}>
            <div className={styles.mapCardHeader}>
              <div className={styles.mapCardTitleGroup}>
                <div className={styles.mapTitle}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00E5FF" strokeWidth="2">
                    <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
                    <line x1="8" y1="2" x2="8" y2="18" />
                    <line x1="16" y1="6" x2="16" y2="22" />
                  </svg>
                  <span>FLOOD RISK MAP</span>
                </div>
                <div className={styles.liveSimBadge}>
                  <span className={styles.liveSimDot} />
                  <span>Live Simulation</span>
                </div>
              </div>

              <div style={{ fontSize: '11px', color: '#94A3B8' }}>
                Spatial Resolution: <strong style={{ color: '#00E5FF' }}>30m Copernicus DEM</strong>
              </div>
            </div>

            {/* 3D Nairobi Flood Risk Map with Interactive OpenStreetMap Buildings */}
            <NairobiMap3D />
          </div>

          {/* ---------------------------------------------------------------
              RIGHT COLUMN: PORTFOLIO AT A GLANCE + CONTINUOUS LEARNING
              --------------------------------------------------------------- */}
          <div className={styles.rightColumn}>
            {/* 7A. PORTFOLIO AT A GLANCE */}
            <div className={styles.portfolioCard}>
              <div className={styles.portfolioHeader}>
                <div className={styles.portfolioTitle}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00E5FF" strokeWidth="2">
                    <rect x="2" y="3" width="20" height="14" rx="2" />
                    <line x1="8" y1="21" x2="16" y2="21" />
                    <line x1="12" y1="17" x2="12" y2="21" />
                  </svg>
                  <span>PORTFOLIO AT A GLANCE</span>
                </div>
                <span className={styles.demoTag}>(Illustrative / Demo)</span>
              </div>

              <div className={styles.kpiRow}>
                {/* KPI 1 */}
                <div className={styles.kpiCol}>
                  <div className={styles.kpiTitle}>Total Insured Value (TIV)</div>
                  <div className={styles.kpiNumber}>{dynamicTiv}</div>
                  <div className={styles.statusBadgeSuccess}>
                    <span>●</span>
                    <span>COMPUTED</span>
                  </div>
                </div>

                {/* KPI 2 */}
                <div className={styles.kpiCol}>
                  <div className={styles.kpiTitle}>AAL (Expected Loss)</div>
                  <div className={styles.kpiNumber}>{dynamicAal}</div>
                  <div className={styles.statusBadgeSuccess}>
                    <span>●</span>
                    <span>COMPUTED</span>
                  </div>
                </div>

                {/* KPI 3 */}
                <div className={styles.kpiCol}>
                  <div className={styles.kpiTitle}>TVaR 99 (Tail Average)</div>
                  <div className={styles.kpiNumber}>{dynamicTvar}</div>
                  <div className={styles.statusBadgeSuccess}>
                    <span>●</span>
                    <span>COMPUTED</span>
                  </div>
                </div>

                {/* KPI 4 */}
                <div className={styles.kpiCol}>
                  <div className={styles.kpiTitle}>Active Exposures</div>
                  <div className={styles.kpiNumber}>{dynamicExposures}</div>
                  <div className={styles.statusBadgePending}>
                    <span>⚠️</span>
                    <span>+3 pending</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 7B. CONTINUOUS LEARNING MODULE */}
            <div className={styles.learningCard}>
              <div className={styles.learningHeader}>
                <svg className={styles.infinityIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18.178 8c5.096 0 5.096 8 0 8-2.678 0-4.407-2.302-6.178-5-1.77-2.698-3.5-5-6.178-5-5.096 0-5.096 8 0 8 2.678 0 4.407-2.302 6.178-5 1.77-2.698 3.5-5 6.178-5z" />
                </svg>
                <div>
                  <div className={styles.learningTitle}>CONTINUOUS LEARNING</div>
                  <div className={styles.learningSubtitle}>Better data. Better models. Better decisions.</div>
                </div>
              </div>

              {/* 4-Step Flow with Icons & Arrows */}
              <div className={styles.learningPipeline}>
                {/* Step 1: Observed Floods */}
                <div
                  className={styles.learningStep}
                  onClick={() => setShowLearningDetail('floods')}
                >
                  <div className={styles.learningStepIconCircle}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M2 12c1.5-1.5 3.5-1.5 5 0s3.5 1.5 5 0 3.5-1.5 5 0 3.5 1.5 5 0" />
                      <path d="M2 18c1.5-1.5 3.5-1.5 5 0s3.5 1.5 5 0 3.5-1.5 5 0 3.5 1.5 5 0" />
                    </svg>
                  </div>
                  <div className={styles.learningStepLabel}>Observed Floods + Claims</div>
                </div>

                <div className={styles.learningArrow}>→</div>

                {/* Step 2: Validation */}
                <div
                  className={styles.learningStep}
                  onClick={() => setShowLearningDetail('validation')}
                >
                  <div className={styles.learningStepIconCircle}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                      <polyline points="9 12 11 14 15 10" />
                    </svg>
                  </div>
                  <div className={styles.learningStepLabel}>Validation</div>
                </div>

                <div className={styles.learningArrow}>→</div>

                {/* Step 3: Calibration */}
                <div
                  className={styles.learningStep}
                  onClick={() => setShowLearningDetail('calibration')}
                >
                  <div className={styles.learningStepIconCircle}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="3" />
                      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                    </svg>
                  </div>
                  <div className={styles.learningStepLabel}>Calibration</div>
                </div>

                <div className={styles.learningArrow}>→</div>

                {/* Step 4: Model Update */}
                <div
                  className={styles.learningStep}
                  onClick={() => setShowLearningDetail('update')}
                >
                  <div className={styles.learningStepIconCircle}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <ellipse cx="12" cy="5" rx="9" ry="3" />
                      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                    </svg>
                  </div>
                  <div className={styles.learningStepLabel}>Model Update</div>
                </div>

                {/* Looping return track at bottom */}
                <div className={styles.loopbackTrack}>
                  <div className={styles.loopbackArrow} />
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* ===================================================================
          8. CROSS-CUTTING FOOTER
          =================================================================== */}
      <footer className={styles.crossCuttingFooter}>
        <div className={styles.footerLeft}>
          <div className={styles.footerBadge}>
            <svg className={styles.footerShieldSvg} viewBox="0 0 24 24">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <polyline points="9 12 11 14 15 10" />
            </svg>
            <span>CROSS-CUTTING</span>
          </div>

          <div className={styles.footerDivider} />

          <div className={styles.footerLinksList}>
            {[
              'Governance',
              'Security',
              'Audit',
              'Model Registry',
              'Uncertainty',
              'Validation',
              'Disaster Recovery',
            ].map((item, idx, arr) => (
              <span key={item} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  type="button"
                  className={styles.footerLinkBtn}
                  onClick={() => setCrossCuttingModal(item)}
                >
                  {item}
                </button>
                {idx < arr.length - 1 && <span className={styles.footerDot}>•</span>}
              </span>
            ))}
          </div>
        </div>

        <div className={styles.footerRight}>
          Measured risk. Greater resilience.
        </div>
      </footer>

      {/* ===================================================================
          9. TARGET ARCHITECTURE & COMPLETE WORKFLOW MODAL (Image 2)
          =================================================================== */}
      {isWorkflowOpen && (
        <div className={styles.workflowDrawer} onClick={() => setIsWorkflowOpen(false)}>
          <div className={styles.workflowBox} onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className={styles.workflowBoxHeader}>
              <div>
                <div className={styles.workflowMainTitle}>
                  Target Architecture / Proposed Kenya Re Flood CAT Platform
                </div>
                <div className={styles.workflowMainSubtitle}>
                  From Data to Decisions — Smarter Flood Risk Intelligence for Kenya Re
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  type="button"
                  className={styles.runPortfolioBtn}
                  onClick={handleRunPipelineSimulation}
                  disabled={isPipelineRunning}
                >
                  {isPipelineRunning ? '⚙️ Simulating 11 Stages…' : '▶ Execute 11-Stage Pipeline'}
                </button>
                <button
                  type="button"
                  className={styles.workflowCloseBtn}
                  onClick={() => setIsWorkflowOpen(false)}
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Workflow Body: 11 Steps List + Loopback Sidebar */}
            <div className={styles.workflowBody}>
              <div className={styles.workflowStepsColumn}>
                {WORKFLOW_STEPS.map((step, index) => {
                  const isActive = selectedWorkflowStep.id === step.id;
                  const isCurrentlyRunning = activeRunningStep === index;
                  return (
                    <div
                      key={step.id}
                      className={`${styles.workflowStepItem} ${isActive ? styles.workflowStepActive : ''} ${step.color === 'purple' ? styles.workflowStepPurple : ''}`}
                      onClick={() => setSelectedWorkflowStep(step)}
                    >
                      <div
                        className={`${styles.stepIconBadge} ${step.color === 'purple' ? styles.stepIconPurple : ''}`}
                      >
                        {step.number}
                      </div>

                      <div className={styles.stepContent}>
                        <div className={styles.stepName}>{step.title}</div>
                        <div className={styles.stepDesc}>{step.desc}</div>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                        <span className={styles.stepStatusTag}>
                          {isCurrentlyRunning ? '⚡ COMPUTING' : '✓ VERIFIED'}
                        </span>
                        <span style={{ fontSize: '10.5px', color: '#64748B', fontFamily: 'monospace' }}>
                          {step.latency}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Sidebar with Loopback and Stage Inspector */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '18px', width: '310px' }}>
                {/* Loopback Architecture Card */}
                <div className={styles.workflowLoopCard}>
                  <svg className={styles.loopSyncIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="23 4 23 10 17 10" />
                    <polyline points="1 20 1 14 7 14" />
                    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
                  </svg>
                  <div className={styles.loopText}>
                    Observed floods + claims → validation → calibration → model update
                  </div>
                  <span style={{ fontSize: '10.5px', color: '#00E5FF', fontWeight: 700 }}>
                    Continuous Actuarial Feedback
                  </span>
                </div>

                {/* Selected Stage Detail Panel */}
                <div
                  style={{
                    background: 'rgba(6, 14, 30, 0.9)',
                    border: '1px solid rgba(0, 229, 255, 0.25)',
                    borderRadius: '12px',
                    padding: '18px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px',
                  }}
                >
                  <div style={{ fontSize: '12px', color: '#00E5FF', fontWeight: 800, textTransform: 'uppercase' }}>
                    Stage Inspector: Step {selectedWorkflowStep.number}
                  </div>
                  <div style={{ fontSize: '14px', fontWeight: 800, color: '#ffffff' }}>
                    {selectedWorkflowStep.title}
                  </div>
                  <div style={{ fontSize: '12px', color: '#94A3B8', lineHeight: 1.4 }}>
                    {selectedWorkflowStep.desc}
                  </div>

                  <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                    <div style={{ fontSize: '11px', color: '#CBD5E1', marginBottom: '4px' }}>
                      Audit Assurance Hash:
                    </div>
                    <code style={{ fontSize: '10px', color: '#00E5FF', wordBreak: 'break-all' }}>
                      sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1f...
                    </code>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          10. HOTSPOT DETAIL POPOVER MODAL
          =================================================================== */}
      {selectedHotspot && (
        <div className={styles.detailModalOverlay} onClick={() => setSelectedHotspot(null)}>
          <div className={styles.detailModalCard} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>{selectedHotspot.name}</div>
              <button
                type="button"
                className={styles.modalCloseBtn}
                onClick={() => setSelectedHotspot(null)}
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ background: 'rgba(255,255,255,0.04)', padding: '10px 14px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '11px', color: '#94A3B8' }}>Basin Classification</div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: '#00E5FF' }}>
                    {selectedHotspot.region}
                  </div>
                </div>

                <div style={{ background: 'rgba(255,255,255,0.04)', padding: '10px 14px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '11px', color: '#94A3B8' }}>Peak Flood Depth</div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: '#EF4444' }}>
                    {selectedHotspot.depth}
                  </div>
                </div>

                <div style={{ background: 'rgba(255,255,255,0.04)', padding: '10px 14px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '11px', color: '#94A3B8' }}>TIV at Risk</div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: '#ffffff' }}>
                    {selectedHotspot.tiv}
                  </div>
                </div>

                <div style={{ background: 'rgba(255,255,255,0.04)', padding: '10px 14px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '11px', color: '#94A3B8' }}>Building Count</div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: '#ffffff' }}>
                    {selectedHotspot.insuredBuildings} Insured / {selectedHotspot.uninsuredBuildings} Total
                  </div>
                </div>
              </div>

              <div
                style={{
                  background: 'rgba(0, 229, 255, 0.08)',
                  border: '1px solid rgba(0, 229, 255, 0.25)',
                  borderRadius: '8px',
                  padding: '12px 14px',
                }}
              >
                <div style={{ fontSize: '11.5px', fontWeight: 700, color: '#00E5FF', marginBottom: '4px' }}>
                  Underwriter Actionable Recommendation:
                </div>
                <div style={{ fontSize: '12.5px', color: '#ffffff' }}>
                  {selectedHotspot.rec}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          11. DOMAIN DRAWER MODAL (DATA, RISK, FINANCE, DECISIONS)
          =================================================================== */}
      {activeDomainDrawer && (
        <div className={styles.detailModalOverlay} onClick={() => setActiveDomainDrawer(null)}>
          <div className={styles.detailModalCard} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>{activeDomainDrawer} Domain Console</div>
              <button
                type="button"
                className={styles.modalCloseBtn}
                onClick={() => setActiveDomainDrawer(null)}
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '13px', color: '#CBD5E1' }}>
              {activeDomainDrawer === 'DATA' && (
                <>
                  <p>
                    <strong>Data Intake & Geocoding:</strong> Ingests portfolio schedules across Kenya, validating geographic coordinates against official boundaries and digital elevation models.
                  </p>
                  <div style={{ padding: '12px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', border: '1px solid #3b82f6' }}>
                    ✓ 197 Assets Geocoded · 0 Coordinate Breaches · Confidence Score 99.4%
                  </div>
                </>
              )}

              {activeDomainDrawer === 'RISK MODELLING' && (
                <>
                  <p>
                    <strong>Hazard & Stochastic Engine:</strong> Calibrated with Kenya Meteorological Department historical records, Copernicus 30m DEM, and Athi/Tana basin hydrodynamic models.
                  </p>
                  <div style={{ padding: '12px', background: 'rgba(0, 229, 255, 0.1)', borderRadius: '8px', border: '1px solid #00E5FF' }}>
                    ✓ 10,000-Year Event Set Loaded · 8,420 Plausible Kenyan Flood Events
                  </div>
                </>
              )}

              {activeDomainDrawer === 'FINANCE' && (
                <>
                  <p>
                    <strong>Reinsurance Financial Structure:</strong> Excess of Loss (XOL), Quota Share, and Surplus treaty terms mapped to ground-up vulnerability damage curves.
                  </p>
                  <div style={{ padding: '12px', background: 'rgba(245, 158, 11, 0.1)', borderRadius: '8px', border: '1px solid #f59e0b' }}>
                    ✓ Portfolio TIV KES 280.0M · AAL KES 128.87M · TVaR 99 KES 227.6M
                  </div>
                </>
              )}

              {activeDomainDrawer === 'DECISIONS' && (
                <>
                  <p>
                    <strong>Agentic AI & Human Governance:</strong> Multi-agent explanations with counterfactual analysis. Strict rule: AI NEVER calculates financial losses itself.
                  </p>
                  <div style={{ padding: '12px', background: 'rgba(139, 92, 246, 0.1)', borderRadius: '8px', border: '1px solid #8b5cf6' }}>
                    ✓ Human Oversight Required for Treaty Reinsurances &gt; KES 50M
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          12. CROSS-CUTTING DETAIL MODAL
          =================================================================== */}
      {crossCuttingModal && (
        <div className={styles.detailModalOverlay} onClick={() => setCrossCuttingModal(null)}>
          <div className={styles.detailModalCard} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>Cross-Cutting: {crossCuttingModal}</div>
              <button
                type="button"
                className={styles.modalCloseBtn}
                onClick={() => setCrossCuttingModal(null)}
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '13px', color: '#CBD5E1' }}>
              <p>
                <strong>Kenya Re Enterprise Assurance:</strong> This cross-cutting capability runs across all 11 stages of the catastrophe modeling lifecycle.
              </p>
              <div
                style={{
                  background: 'rgba(0, 229, 255, 0.08)',
                  padding: '14px',
                  borderRadius: '8px',
                  border: '1px solid rgba(0, 229, 255, 0.25)',
                }}
              >
                <div style={{ fontWeight: 700, color: '#00E5FF', marginBottom: '4px' }}>
                  Status: ACTIVE & COMPLIANT
                </div>
                <div style={{ fontSize: '12px', color: '#94A3B8' }}>
                  Audited according to Kenya Insurance Regulatory Authority (IRA) solvency II cat guidelines and Kenya Re risk appetite statement.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          13. ABOUT MODAL
          =================================================================== */}
      {activeNav === 'about' && (
        <div className={styles.detailModalOverlay} onClick={() => setActiveNav('home')}>
          <div className={styles.detailModalCard} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>About Kenya Re Flood Risk Intelligence</div>
              <button
                type="button"
                className={styles.modalCloseBtn}
                onClick={() => setActiveNav('home')}
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '13px', color: '#CBD5E1' }}>
              <p>
                <strong>FLOODTAIL</strong> is Kenya Re’s flagship Catastrophe Risk Analytics Platform engineered for precision underwriting, stochastic hazard simulation, and reinsurance capital optimization.
              </p>
              <p>
                Combining deterministic actuarial math, high-resolution 30m digital elevation mapping, and agentic intelligence, FLOODTAIL empowers underwriters to make rapid, defensible, and audited risk decisions.
              </p>
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '10px', fontSize: '11px', color: '#94A3B8' }}>
                © 2026 Kenya Reinsurance Corporation Ltd. All Rights Reserved.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
