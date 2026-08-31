"use client";

import React, { useEffect, useState, useCallback } from 'react';
import { usePathname } from 'next/navigation';
import { initI18n } from '../../i18n/client';
import { useTranslation } from 'react-i18next';
import { getBackendUrl } from '../../../utils/api';

interface StrategyVersion {
  name: string;
  version: string;
  strategy_type?: string;
  created_at?: string;
}

interface StrategyRun {
  id: string;
  strategy_name: string;
  symbol: string;
  status?: string;
  created_at?: string;
}

export default function ResearchPage() {
  const pathname = usePathname();
  const lng = pathname?.split('/')[1] || 'en';
  initI18n(lng);
  const { t } = useTranslation('translation');

  const backendUrl = getBackendUrl();
  const [strategies, setStrategies] = useState<StrategyVersion[]>([]);
  const [runs, setRuns] = useState<StrategyRun[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchResearch = useCallback(async () => {
    setLoading(true);
    try {
      const [strategiesRes, runsRes] = await Promise.all([
        fetch(`${backendUrl}/v1/research/strategies`).catch(() => null),
        fetch(`${backendUrl}/v1/research/runs`).catch(() => null),
      ]);

      if (strategiesRes && strategiesRes.ok) {
        const data = await strategiesRes.json();
        setStrategies(Array.isArray(data) ? data : []);
      }

      if (runsRes && runsRes.ok) {
        const data = await runsRes.json();
        setRuns(Array.isArray(data) ? data : []);
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [backendUrl]);

  useEffect(() => {
    fetchResearch();
  }, [fetchResearch]);

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '32px 24px' }}>
      <div style={{ marginBottom: '28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: '700', marginBottom: '8px' }}>
            Video EA Research & Quant Laboratory
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
            Deterministic walk-forward optimization, Monte Carlo stress testing, and agentic parameter exploration.
          </p>
        </div>
        <div className="layout-stats" style={{ marginBottom: 0 }}>
          <div className="metric-card">
            <span className="metric-label">Strategies</span>
            <strong className="metric-value" style={{ color: 'var(--color-accent)' }}>{strategies.length}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Runs</span>
            <strong className="metric-value" style={{ color: 'var(--color-primary)' }}>{runs.length}</strong>
          </div>
        </div>
      </div>

      <div className="layout-grid" style={{ gap: '28px' }}>
        <div className="glass-card animate-fade-in">
          <h3 className="h3" style={{ marginBottom: '20px' }}>Registered Strategies</h3>
          {strategies.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {strategies.slice(0, 20).map((strategy, idx) => (
                <div key={`${strategy.name}-${strategy.version}-${idx}`} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)' }}>
                  <div>
                    <strong style={{ fontSize: '14px', color: 'var(--text-primary)' }}>{strategy.name}</strong>
                    <div style={{ marginTop: '4px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      <span className="badge badge-secondary">v{strategy.version}</span>
                      {strategy.strategy_type && <span className="badge badge-primary">{strategy.strategy_type}</span>}
                    </div>
                  </div>
                  <span className="text-secondary" style={{ fontSize: '12px' }}>
                    {strategy.created_at ? new Date(strategy.created_at).toLocaleDateString() : ''}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)', fontSize: '13px' }}>
              {loading ? 'Loading strategies...' : 'No strategies registered'}
            </div>
          )}
        </div>

        <div className="glass-card animate-fade-in">
          <h3 className="h3" style={{ marginBottom: '20px' }}>Recent Research Runs</h3>
          {runs.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {runs.slice(0, 20).map((run, idx) => (
                <div key={`${run.id || run.strategy_name}-${idx}`} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)' }}>
                  <div>
                    <strong style={{ fontSize: '14px', color: 'var(--text-primary)' }}>{run.strategy_name}</strong>
                    <div style={{ marginTop: '4px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      <span className="badge badge-primary">{run.symbol}</span>
                      {run.status && <span className={`badge ${run.status === 'completed' ? 'badge-accent' : run.status === 'failed' ? 'badge-danger' : 'badge-secondary'}`}>{run.status}</span>}
                    </div>
                  </div>
                  <span className="text-secondary" style={{ fontSize: '12px' }}>
                    {run.created_at ? new Date(run.created_at).toLocaleString() : ''}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)', fontSize: '13px' }}>
              {loading ? 'Loading runs...' : 'No research runs yet'}
            </div>
          )}
        </div>
      </div>

      <div className="glass-card animate-fade-in" style={{ marginTop: '28px' }}>
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
