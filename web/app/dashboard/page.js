'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import styles from './dashboard.module.css';

const AGENTS = [
  { id: 1, name: 'ExposureIntelligence', desc: 'DQ Audit & Geocoding', status: 'PASSED', time: '14ms' },
  { id: 2, name: 'HazardAnalysis', desc: 'Spatial Footprint Match', status: 'PASSED', time: '28ms' },
  { id: 3, name: 'VulnerabilityReview', desc: 'Depth-Damage Curves', status: 'WARNING', time: '18ms' },
  { id: 4, name: 'LossAnalysis', desc: 'ELT/YLT Reconciliation', status: 'PASSED', time: '42ms' },
  { id: 5, name: 'TailRisk', desc: 'VaR/TVaR 99.6% Allocation', status: 'PASSED', time: '65ms' },
  { id: 6, name: 'Accumulation', desc: 'HHI & Co-Hit Evaluation', status: 'PASSED', time: '31ms' },
  { id: 7, name: 'PricingIntelligence', desc: 'Cost of Capital Waterfall', status: 'PASSED', time: '22ms' },
  { id: 8, name: 'Scenario', desc: 'CRN Marginal TVaR', status: 'PASSED', time: '54ms' },
  { id: 9, name: 'RiskAppetite', desc: 'Underwriting Governance', status: 'PASSED', time: '19ms' },
  { id: 10, name: 'DecisionSupport', desc: 'Evidence Package Builder', status: 'PASSED', time: '33ms' },
  { id: 11, name: 'Governance', desc: 'Audit Readiness Cert', status: 'PASSED', time: '12ms' },
];

const POLICIES = [
  {
    id: 'POL-KE-001',
    region: 'Nairobi Basin (Industrial)',
    tiv: 'KES 850,000,000',
    aal: 'KES 8,450,000',
    tailShare: '24.2%',
    marginalTvar: 'KES 42,100,000',
    technicalPremium: 'KES 14,850,000',
    status: 'ESCALATE',
    reason: 'Critical Industrial Tail Concentration > 20%',
    confidence: '98.4%'
  },
  {
    id: 'POL-KE-002',
    region: 'Mombasa Port Facility',
    tiv: 'KES 1,200,000,000',
    aal: 'KES 9,800,000',
    tailShare: '18.6%',
    marginalTvar: 'KES 31,500,000',
    technicalPremium: 'KES 16,200,000',
    status: 'REVIEW',
    reason: 'Tidal & Pluvial Co-Hit Risk (Zone A)',
    confidence: '96.1%'
  },
  {
    id: 'POL-KE-003',
    region: 'Kisumu Lake Commercial',
    tiv: 'KES 420,000,000',
    aal: 'KES 2,950,000',
    tailShare: '6.4%',
    marginalTvar: 'KES 9,200,000',
    technicalPremium: 'KES 4,800,000',
    status: 'ACCEPT',
    reason: 'Well Mitigated Elevation Profile',
    confidence: '99.2%'
  },
  {
    id: 'POL-KE-004',
    region: 'Tana River Agribusiness',
    tiv: 'KES 680,000,000',
    aal: 'KES 5,100,000',
    tailShare: '11.8%',
    marginalTvar: 'KES 18,400,000',
    technicalPremium: 'KES 8,900,000',
    status: 'REVIEW',
    reason: 'High Frequency Seasonal Riverine Inundation',
    confidence: '94.5%'
  },
  {
    id: 'POL-KE-005',
    region: 'Nakuru Town Retail Hub',
    tiv: 'KES 340,000,000',
    aal: 'KES 1,850,000',
    tailShare: '4.1%',
    marginalTvar: 'KES 5,600,000',
    technicalPremium: 'KES 3,100,000',
    status: 'ACCEPT',
    reason: 'Low Basin Hazard Exposure',
    confidence: '99.5%'
  },
  {
    id: 'POL-KE-006',
    region: 'Garissa Logistics Depot',
    tiv: 'KES 290,000,000',
    aal: 'KES 2,400,000',
    tailShare: '5.2%',
    marginalTvar: 'KES 7,100,000',
    technicalPremium: 'KES 3,950,000',
    status: 'ACCEPT',
    reason: 'Low Elevation but Moderate Value Density',
    confidence: '97.8%'
  },
];

export default function DashboardPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('overview');
  const [isRunningSim, setIsRunningSim] = useState(false);
  const [activeAgentIndex, setActiveAgentIndex] = useState(null);
  const [selectedPolicy, setSelectedPolicy] = useState(POLICIES[0]);

  const handleRunPipeline = () => {
    setIsRunningSim(true);
    let step = 0;
    const interval = setInterval(() => {
      setActiveAgentIndex(step);
      step++;
      if (step >= AGENTS.length) {
        clearInterval(interval);
        setTimeout(() => {
          setIsRunningSim(false);
          setActiveAgentIndex(null);
        }, 500);
      }
    }, 180);
  };

  const handleSignOut = () => {
    router.push('/');
  };

  return (
    <div className={styles.dashboard}>
      {/* Top Navbar */}
      <header className={styles.topNav}>
        <div className={styles.brandGroup}>
          <div className={styles.brandLogo}>
            <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
              <polygon points="12,10 38,10 20,90 12,90" fill="#E52320" />
              <polygon points="26,10 68,10 52,44 36,44" fill="#FFFFFF" />
              <polygon points="48,48 90,10 72,90 54,58" fill="#00E5FF" />
              <polygon points="30,54 48,90 34,90 18,58" fill="#0066CC" />
            </svg>
          </div>
          <div>
            <div className={styles.brandTitle}>
              KENYA <span>RE</span> FLOODTAIL
            </div>
            <div className={styles.brandSubtitle}>Catastrophe Intelligence & Underwriting Engine</div>
          </div>
        </div>

        <div className={styles.headerMetrics}>
          <div className={styles.statusPill}>
            <span className={styles.statusDot} />
            <span>11 AGENTS VERIFIED · AUDIT READY</span>
          </div>

          <div className={styles.userProfile}>
            <div className={styles.avatar}>KR</div>
            <div className={styles.userInfo}>
              <div className={styles.userName}>Dr. Sarah Ochieng</div>
              <div className={styles.userRole}>Chief Catastrophe Underwriter</div>
            </div>
          </div>

          <button type="button" className={styles.signOutBtn} onClick={handleSignOut}>
            Sign Out
          </button>
        </div>
      </header>

      {/* Subheader / Tabs */}
      <div className={styles.subHeader}>
        <nav className={styles.tabNav} aria-label="Dashboard views">
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === 'overview' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            📊 Executive Overview
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === 'pipeline' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('pipeline')}
          >
            ⚡ 11-Agent Trace & Graph
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === 'decisions' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('decisions')}
          >
            🛡️ Underwriting Evidence
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === 'pricing' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('pricing')}
          >
            💰 Technical Pricing Waterfall
          </button>
        </nav>

        <button
          type="button"
          className={styles.quickRunBtn}
          onClick={handleRunPipeline}
          disabled={isRunningSim}
        >
          {isRunningSim ? '⚙️ Executing Pipeline…' : '▶ Run 10,000-Yr Simulation'}
        </button>
      </div>

      {/* Main Content Area */}
      <main className={styles.mainContainer}>
        {/* KPI Grid */}
        <section className={styles.kpiGrid} aria-label="Key Performance Indicators">
          <div className={styles.kpiCard}>
            <div className={styles.kpiLabel}>Total Insured Value (TIV)</div>
            <div className={`${styles.kpiValue} ${styles.kpiCyan}`}>KES 4.85B</div>
            <div className={styles.kpiSub}>124 Geocoded Commercial Risks</div>
          </div>

          <div className={styles.kpiCard}>
            <div className={styles.kpiLabel}>Portfolio AAL (Expected Loss)</div>
            <div className={styles.kpiValue}>KES 38.42M</div>
            <div className={styles.kpiSub}>0.79% Portfolio Burning Cost</div>
          </div>

          <div className={styles.kpiCard}>
            <div className={styles.kpiLabel}>1-in-250 TVaR (99.6% Tail)</div>
            <div className={`${styles.kpiValue} ${styles.kpiRed}`}>KES 284.10M</div>
            <div className={styles.kpiSub}>Tail Risk Multiplier: 7.39x AAL</div>
          </div>

          <div className={styles.kpiCard}>
            <div className={styles.kpiLabel}>Technical Premium Target</div>
            <div className={`${styles.kpiValue} ${styles.kpiGreen}`}>KES 58.74M</div>
            <div className={styles.kpiSub}>Includes 10% CoC & Expense</div>
          </div>

          <div className={styles.kpiCard}>
            <div className={styles.kpiLabel}>Regional HHI Index</div>
            <div className={`${styles.kpiValue} ${styles.kpiAmber}`}>0.182</div>
            <div className={styles.kpiSub}>Moderate Concentration (Nairobi 42%)</div>
          </div>
        </section>

        {/* 11 Agent Workflow Pipeline Rail */}
        <section className={styles.pipelineSection}>
          <div className={styles.pipelineHeader}>
            <div className={styles.pipelineTitle}>
              <span>🤖 Multi-Agent Catastrophe Decision Pipeline (11 Steps)</span>
            </div>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Deterministic Actuarial Graph · Zero Stochastic Inference
            </span>
          </div>

          <div className={styles.pipelineRail}>
            {AGENTS.map((agent, index) => {
              const isCurrent = activeAgentIndex === index;
              return (
                <div key={agent.id} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div
                    className={styles.agentStep}
                    style={{
                      borderColor: isCurrent ? 'var(--cyan)' : undefined,
                      boxShadow: isCurrent ? '0 0 16px rgba(0,229,255,0.4)' : undefined,
                      background: isCurrent ? 'rgba(0,229,255,0.15)' : undefined,
                    }}
                  >
                    <div className={styles.agentNumber}>STEP {agent.id}</div>
                    <div className={styles.agentName}>{agent.name}</div>
                    <div
                      className={styles.agentStatus}
                      style={{ color: agent.status === 'WARNING' ? '#F59E0B' : '#10B981' }}
                    >
                      {agent.status} ({agent.time})
                    </div>
                  </div>
                  {index < AGENTS.length - 1 && <span className={styles.agentArrow}>→</span>}
                </div>
              );
            })}
          </div>
        </section>

        {/* Dynamic Tab Views */}
        {activeTab === 'overview' && (
          <div className={styles.gridTwoCol}>
            {/* Kenya Spatial Risk Footprint */}
            <div className={styles.cardBox}>
              <div className={styles.cardBoxHeader}>
                <div className={styles.cardBoxTitle}>
                  <span>🗺️ Kenya Flood Hazard Footprint & Basin Exposure</span>
                </div>
                <span style={{ fontSize: '12px', color: 'var(--cyan)' }}>High-Resolution 30m DEM Grid</span>
              </div>

              <div style={{ position: 'relative', height: '360px', background: '#020713', borderRadius: '12px', overflow: 'hidden', border: '1px solid rgba(0,229,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <svg viewBox="0 0 640 400" width="100%" height="100%">
                  <path
                    d="M200,60 L260,40 L380,90 L460,160 L450,260 L480,310 L410,350 L370,390 L330,395 L250,350 L190,330 L150,280 L130,220 L150,140 Z"
                    stroke="#00E5FF"
                    strokeWidth="1.8"
                    fill="rgba(0, 229, 255, 0.03)"
                  />
                  {/* Rivers */}
                  <path d="M220,230 Q270,250 330,280 T380,340" stroke="#00E5FF" strokeWidth="1.5" fill="none" opacity="0.8" />
                  <path d="M170,250 Q220,240 270,230 T320,200" stroke="#22d3ee" strokeWidth="1.2" fill="none" opacity="0.6" />

                  {/* Hotspots */}
                  <g transform="translate(230,260)">
                    <circle r="14" fill="rgba(239,68,68,0.25)" />
                    <circle r="6" fill="#EF4444" />
                    <text x="14" y="4" fill="#ffffff" fontSize="11" fontWeight="700">Nairobi Industrial (KES 1.8B TIV)</text>
                  </g>
                  <g transform="translate(370,330)">
                    <circle r="12" fill="rgba(245,158,11,0.25)" />
                    <circle r="5" fill="#F59E0B" />
                    <text x="12" y="4" fill="#ffffff" fontSize="11" fontWeight="700">Mombasa Port (KES 1.2B TIV)</text>
                  </g>
                  <g transform="translate(150,265)">
                    <circle r="10" fill="rgba(16,185,129,0.25)" />
                    <circle r="5" fill="#10B981" />
                    <text x="-115" y="4" fill="#ffffff" fontSize="11" fontWeight="700">Kisumu Lake Basin</text>
                  </g>
                  <g transform="translate(330,210)">
                    <circle r="8" fill="rgba(0,229,255,0.25)" />
                    <circle r="4" fill="#00E5FF" />
                    <text x="10" y="4" fill="#94A3B8" fontSize="10">Tana Delta Agribusiness</text>
                  </g>
                </svg>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                <span>🔴 Critical Tail Hotspot</span>
                <span>🟡 Pluvial/Tidal Review Zone</span>
                <span>🟢 Mitigated Elevation Zone</span>
                <span>🔵 Riverine Corridor</span>
              </div>
            </div>

            {/* Regional Accumulation Breakdown */}
            <div className={styles.cardBox}>
              <div className={styles.cardBoxHeader}>
                <div className={styles.cardBoxTitle}>
                  <span>📊 Portfolio Regional Concentration</span>
                </div>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>HHI = 0.182</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600 }}>Nairobi Metropolitan Basin</span>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--cyan)' }}>42.4% (KES 2.06B)</span>
                  </div>
                  <div style={{ height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: '42.4%', height: '100%', background: 'var(--cyan)', borderRadius: '4px' }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600 }}>Mombasa Coastal Zone</span>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--blue-kr)' }}>24.7% (KES 1.20B)</span>
                  </div>
                  <div style={{ height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: '24.7%', height: '100%', background: '#38bdf8', borderRadius: '4px' }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600 }}>Tana River Agricultural Corridor</span>
                    <span style={{ fontFamily: 'var(--font-mono)' }}>14.0% (KES 680M)</span>
                  </div>
                  <div style={{ height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: '14.0%', height: '100%', background: '#818cf8', borderRadius: '4px' }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600 }}>Kisumu Lake Victoria Basin</span>
                    <span style={{ fontFamily: 'var(--font-mono)' }}>8.7% (KES 420M)</span>
                  </div>
                  <div style={{ height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: '8.7%', height: '100%', background: '#34d399', borderRadius: '4px' }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600 }}>Rift Valley & Others</span>
                    <span style={{ fontFamily: 'var(--font-mono)' }}>10.2% (KES 490M)</span>
                  </div>
                  <div style={{ height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: '10.2%', height: '100%', background: '#94a3b8', borderRadius: '4px' }} />
                  </div>
                </div>
              </div>

              <div style={{ marginTop: '24px', padding: '14px', background: 'rgba(0,229,255,0.05)', borderRadius: '10px', border: '1px solid rgba(0,229,255,0.15)', fontSize: '12px', lineHeight: '1.5' }}>
                💡 <strong>Governance Audit Note:</strong> Nairobi accumulation remains below the 45% treaty threshold limit set by the Kenya Re Risk Committee.
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: 11-Agent Trace */}
        {activeTab === 'pipeline' && (
          <div className={styles.cardBox}>
            <div className={styles.cardBoxHeader}>
              <div className={styles.cardBoxTitle}>
                <span>⚙️ Complete Deterministic Workflow Trace (Execution Audit Log)</span>
              </div>
              <span style={{ fontSize: '12px', color: '#10B981' }}>✓ 100% Deterministic & Auditable</span>
            </div>

            <table className={styles.dataTable}>
              <thead>
                <tr>
                  <th>Step</th>
                  <th>Agent Name</th>
                  <th>Core Responsibility</th>
                  <th>Latency</th>
                  <th>Audit Status</th>
                  <th>Reconciliation Check</th>
                </tr>
              </thead>
              <tbody>
                {AGENTS.map((agent) => (
                  <tr key={agent.id}>
                    <td style={{ fontWeight: 700, color: 'var(--cyan)' }}>0{agent.id}</td>
                    <td style={{ fontWeight: 700, color: '#ffffff' }}>{agent.name}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{agent.desc}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{agent.time}</td>
                    <td>
                      <span className={agent.status === 'WARNING' ? styles.badgeReview : styles.badgeAccept}>
                        {agent.status}
                      </span>
                    </td>
                    <td style={{ color: '#10B981', fontWeight: 600 }}>PASSED (Tolerance &lt; 1e-4)</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 3: Decision Evidence */}
        {activeTab === 'decisions' && (
          <div className={styles.cardBox}>
            <div className={styles.cardBoxHeader}>
              <div className={styles.cardBoxTitle}>
                <span>🛡️ Underwriting Decision Support & Evidence Packages</span>
              </div>
              <span style={{ fontSize: '12px', color: 'var(--cyan)' }}>
                Multi-Factor Confidence &amp; Cost of Capital Breakdown
              </span>
            </div>

            <table className={styles.dataTable}>
              <thead>
                <tr>
                  <th>Policy ID</th>
                  <th>Risk Location</th>
                  <th>Insured TIV</th>
                  <th>Annual AAL</th>
                  <th>Tail Share</th>
                  <th>Marginal TVaR</th>
                  <th>Tech Premium</th>
                  <th>Underwriting Action</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {POLICIES.map((p) => (
                  <tr
                    key={p.id}
                    onClick={() => setSelectedPolicy(p)}
                    style={{
                      cursor: 'pointer',
                      background: selectedPolicy.id === p.id ? 'rgba(0,229,255,0.08)' : undefined,
                    }}
                  >
                    <td style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--cyan)' }}>{p.id}</td>
                    <td style={{ fontWeight: 600 }}>{p.region}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{p.tiv}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{p.aal}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: '#EF4444' }}>{p.tailShare}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{p.marginalTvar}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: '#10B981', fontWeight: 700 }}>{p.technicalPremium}</td>
                    <td>
                      <span
                        className={
                          p.status === 'ACCEPT'
                            ? styles.badgeAccept
                            : p.status === 'REVIEW'
                            ? styles.badgeReview
                            : styles.badgeEscalate
                        }
                      >
                        {p.status}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>{p.confidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Selected Policy Evidence Detail Card */}
            {selectedPolicy && (
              <div style={{ marginTop: '24px', padding: '20px', background: 'rgba(8,18,38,0.9)', borderRadius: '12px', border: '1px solid var(--border-default)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--cyan)' }}>
                    Decision Evidence Summary: {selectedPolicy.id} ({selectedPolicy.region})
                  </div>
                  <span className={selectedPolicy.status === 'ACCEPT' ? styles.badgeAccept : selectedPolicy.status === 'REVIEW' ? styles.badgeReview : styles.badgeEscalate}>
                    RECOMMENDATION: {selectedPolicy.status}
                  </span>
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                  <strong>Governance Reason:</strong> {selectedPolicy.reason}<br />
                  <strong>Actuarial Waterfall:</strong> Base Expected Loss ({selectedPolicy.aal}) + Tail Risk Cost of Capital (10% rate on {selectedPolicy.marginalTvar}) + Underwriting Expense = <strong>Technical Target Premium {selectedPolicy.technicalPremium}</strong>.
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Pricing Waterfall */}
        {activeTab === 'pricing' && (
          <div className={styles.gridTwoCol}>
            <div className={styles.cardBox}>
              <div className={styles.cardBoxHeader}>
                <div className={styles.cardBoxTitle}>
                  <span>💰 Technical Pricing Waterfall Architecture</span>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ padding: '14px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', borderLeft: '4px solid var(--cyan)' }}>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Step 1: Expected Loss Component (AAL)</div>
                  <div style={{ fontSize: '20px', fontWeight: 800, color: '#ffffff', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                    KES 38,420,000
                  </div>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>Pure burning cost from 10,000-year stochastic event set</div>
                </div>

                <div style={{ padding: '14px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', borderLeft: '4px solid #818cf8' }}>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Step 2: Tail Risk Capital Charge (10% Cost of Capital on TVaR)</div>
                  <div style={{ fontSize: '20px', fontWeight: 800, color: '#818cf8', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                    + KES 14,480,000
                  </div>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>Allocated based on Euler / CRN marginal tail contribution</div>
                </div>

                <div style={{ padding: '14px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', borderLeft: '4px solid #F59E0B' }}>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Step 3: Operational Expense Loading (10%)</div>
                  <div style={{ fontSize: '20px', fontWeight: 800, color: '#F59E0B', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                    + KES 5,840,000
                  </div>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>Brokerage, model governance, and IRA compliance</div>
                </div>

                <div style={{ padding: '16px', background: 'rgba(16,185,129,0.1)', borderRadius: '8px', border: '1px solid rgba(16,185,129,0.3)' }}>
                  <div style={{ fontSize: '12px', color: '#10B981', fontWeight: 700 }}>Total Technical Target Premium</div>
                  <div style={{ fontSize: '26px', fontWeight: 900, color: '#ffffff', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                    KES 58,740,000
                  </div>
                </div>
              </div>
            </div>

            <div className={styles.cardBox}>
              <div className={styles.cardBoxHeader}>
                <div className={styles.cardBoxTitle}>
                  <span>📈 Loss Exceedance Curve (Return Periods)</span>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span>1-in-10 Year Return (90.0% VaR)</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>KES 42.50M</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span>1-in-50 Year Return (98.0% VaR)</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>KES 112.80M</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span>1-in-100 Year Return (99.0% VaR)</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>KES 178.40M</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--cyan)', fontWeight: 700 }}>1-in-250 Year Return (99.6% VaR)</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--cyan)' }}>KES 245.60M</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: '#EF4444', fontWeight: 700 }}>1-in-250 TVaR (Tail Expected Loss)</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, color: '#EF4444' }}>KES 284.10M</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
