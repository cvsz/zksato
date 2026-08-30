"use client";

import React, { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { initI18n } from '../../i18n/client';
import { useTranslation } from 'react-i18next';
import { getBackendUrl } from '../../../utils/api';

interface TfexAccount {
  account_no: string;
  total_equity: number;
  excess_equity: number;
  margin_usage_pct: number;
  open_positions_count: number;
}

export default function TfexPage() {
  const pathname = usePathname();
  const lng = pathname?.split('/')[1] || 'en';
  initI18n(lng);
  const { t } = useTranslation('translation');

  const backendUrl = getBackendUrl();
  const [account, setAccount] = useState<TfexAccount | null>(null);

  useEffect(() => {
    const fetchTfex = async () => {
      try {
        const res = await fetch(`${backendUrl}/v1/tfex/account`);
        if (res.ok) {
          setAccount(await res.json());
        }
      } catch (err) {
        console.error('Failed to load TFEX account:', err);
      }
    };
    fetchTfex();
  }, [backendUrl]);

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '32px 24px' }}>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: '700', marginBottom: '8px' }}>
          TFEX Derivatives Gateway (SET/TFEX UAT)
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
          Strictly isolated derivative contract registry, margin surveillance, and UAT execution.
        </p>
      </div>

      <div className="layout-stats" style={{ marginBottom: '28px' }}>
        <div className="metric-card">
          <span className="metric-label">Account Number</span>
          <strong className="metric-value">{account?.account_no || 'TFEX-UAT-01'}</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Margin Usage</span>
          <strong className="metric-value" style={{ color: 'var(--color-primary)' }}>
            {(account?.margin_usage_pct ?? 0).toFixed(1)}%
          </strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Execution Mode</span>
          <strong className="metric-value" style={{ color: 'var(--color-accent)' }}>
            UAT Sandbox
          </strong>
        </div>
      </div>

      <div className="glass-card">
        <h3 className="h3" style={{ marginBottom: '16px' }}>Supported TFEX Series</h3>
        <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: '1.6' }}>
          S50 Futures (SET50 Index), GO (Gold Online), and USD/THB currency futures with automated rollover evaluation and pre-trade margin checks.
        </p>
      </div>
    </div>
  );
}
