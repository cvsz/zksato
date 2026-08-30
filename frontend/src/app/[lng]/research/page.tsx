"use client";

import React from 'react';
import { usePathname } from 'next/navigation';
import { initI18n } from '../../i18n/client';
import { useTranslation } from 'react-i18next';

export default function ResearchPage() {
  const pathname = usePathname();
  const lng = pathname?.split('/')[1] || 'en';
  initI18n(lng);
  const { t } = useTranslation('translation');

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '32px 24px' }}>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: '700', marginBottom: '8px' }}>
          Video EA Research & Quant Laboratory
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
          Deterministic walk-forward optimization, Monte Carlo stress testing, and agentic parameter exploration.
        </p>
      </div>

      <div className="layout-stats" style={{ marginBottom: '28px' }}>
        <div className="metric-card">
          <span className="metric-label">Research Status</span>
          <strong className="metric-value" style={{ color: 'var(--color-accent)' }}>OPERATIONAL</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Authority Boundary</span>
          <strong className="metric-value" style={{ color: 'var(--color-primary)' }}>NON-EXECUTING</strong>
        </div>
      </div>

      <div className="glass-card">
        <h3 className="h3" style={{ marginBottom: '16px' }}>Research Modules</h3>
        <ul style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '2' }}>
          <li>Rolling Walk-Forward Analysis (Session-aware in-sample / out-of-sample splits)</li>
          <li>Monte Carlo Trade Stress & Reordering Simulations</li>
          <li>Adverse Grid Whipsaw & Gap Replay Diagnostics</li>
          <li>Continuous Portfolio Value-at-Risk (VaR) & Expected Shortfall (CVaR)</li>
        </ul>
      </div>
    </div>
  );
}
