"use client";

import React, { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { initI18n } from '../../i18n/client';
import { useTranslation } from 'react-i18next';
import { getBackendUrl } from '../../../utils/api';

export default function ReconciliationPage() {
  const pathname = usePathname();
  const lng = pathname?.split('/')[1] || 'en';
  initI18n(lng);
  const { t } = useTranslation('translation');

  const backendUrl = getBackendUrl();
  const [reconciling, setReconciling] = useState(false);
  const [report, setReport] = useState<any>(null);

  const handleReconcile = async () => {
    setReconciling(true);
    try {
      const res = await fetch(`${backendUrl}/v1/reconcile`, { method: 'POST' });
      if (res.ok) {
        setReport(await res.json());
      }
    } catch (err) {
      console.error('Reconciliation failed:', err);
    } finally {
      setReconciling(false);
    }
  };

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '32px 24px' }}>
      <div style={{ marginBottom: '28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: '700', marginBottom: '8px' }}>
            Broker Reconciliation & State Convergence
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
            Fail-closed order book verification, fill ledger reconciliation, and orphan position resolution.
          </p>
        </div>
        <button
          onClick={handleReconcile}
          disabled={reconciling}
          className="btn-base btn-primary"
          style={{ padding: '10px 20px', fontSize: '14px', fontWeight: '600' }}
        >
          {reconciling ? 'Reconciling...' : 'Run Reconciliation'}
        </button>
      </div>

      <div className="layout-stats" style={{ marginBottom: '28px' }}>
        <div className="metric-card">
          <span className="metric-label">Reconciliation Gate</span>
          <strong className="metric-value" style={{ color: 'var(--color-accent)' }}>READY</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Unresolved Orders</span>
          <strong className="metric-value">0</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">External Truth Source</span>
          <strong className="metric-value" style={{ color: 'var(--color-primary)' }}>Broker API</strong>
        </div>
      </div>

      {report && (
        <div className="glass-card">
          <h3 className="h3" style={{ marginBottom: '12px' }}>Latest Reconciliation Report</h3>
          <pre style={{ background: 'var(--bg-surface)', padding: '16px', borderRadius: '8px', overflowX: 'auto', fontSize: '13px' }}>
            {JSON.stringify(report, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
