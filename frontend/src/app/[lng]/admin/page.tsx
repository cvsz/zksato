"use client";

import React, { useEffect, useState, useCallback } from 'react';
import { usePathname } from 'next/navigation';
import { initI18n } from '../../i18n/client';
import { useTranslation } from 'react-i18next';
import { Toast } from '../../../components/Toast';
import { getBackendUrl } from '../../../utils/api';

interface SystemHealth {
  status: string;
  environment?: string;
  execution_mode?: string;
  live_trading_enabled?: boolean;
  kill_switch_active?: boolean;
  services?: Record<string, boolean>;
}

interface BotRecord {
  id: string;
  strategy_name: string;
  symbol: string;
  status: string;
  execution_mode: string;
  last_error?: string | null;
  last_tick_at?: string | null;
  signals_generated?: number;
  orders_submitted?: number;
}

interface AuditRecord {
  id: string;
  timestamp?: string;
  created_at?: string;
  severity?: string;
  message: string;
  event_type?: string;
  details?: unknown;
}

interface RiskRecord {
  id: string;
  symbol?: string;
  decision?: string;
  max_notional?: number;
  allowed_symbols?: string[];
  quantity?: number;
  price?: number;
  created_at?: string;
  timestamp?: string;
}

interface PortfolioRecord {
  total_equity?: number;
  cash?: number;
  positions_value?: number;
  realized_pnl?: number;
  unrealized_pnl?: number;
}

interface WebhookRecord {
  symbol: string;
  exchange?: string;
  created_at?: string;
}

type TabKey = 'overview' | 'performance' | 'bots' | 'risk' | 'history' | 'webhooks';

function StatusDot({ ok, pulse = false }: { ok: boolean; pulse?: boolean }) {
  return (
    <span
      className={`status-dot ${ok ? 'status-dot-up' : 'status-dot-down'}`}
      style={{
        boxShadow: pulse && ok ? '0 0 8px rgba(16,185,129,0.6)' : pulse && !ok ? '0 0 8px rgba(239,68,68,0.6)' : 'none',
        animation: pulse ? 'pulse 2s infinite' : 'none',
      }}
    />
  );
}

function SeverityBadge({ severity }: { severity?: string }) {
  const colors: Record<string, string> = {
    INFO: 'badge-info',
    WARN: 'badge-warning',
    ERROR: 'badge-danger',
    CRITICAL: 'badge-danger',
  };
  const cls = severity ? colors[severity] || 'badge-secondary' : 'badge-secondary';
  return <span className={`badge ${cls}`}>{severity || 'INFO'}</span>;
}

export default function AdminDashboardPage() {
  const pathname = usePathname();
  const lng = pathname?.split('/')[1] || 'en';
  initI18n(lng);
  const { t } = useTranslation('translation');

  const backendUrl = getBackendUrl();

  const [tab, setTab] = useState<TabKey>('overview');
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);

  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [dashboard, setDashboard] = useState<any>(null);
  const [portfolio, setPortfolio] = useState<PortfolioRecord | null>(null);
  const [bots, setBots] = useState<BotRecord[]>([]);
  const [logs, setLogs] = useState<AuditRecord[]>([]);
  const [riskEvaluations, setRiskEvaluations] = useState<RiskRecord[]>([]);
  const [webhooks, setWebhooks] = useState<WebhookRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const showToast = useCallback((msg: string, type: 'success' | 'error') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [
        healthRes,
        dashboardRes,
        portfolioRes,
        botsRes,
        logsRes,
        riskRes,
        webhooksRes,
      ] = await Promise.all([
        fetch(`${backendUrl}/health`).catch(() => null),
        fetch(`${backendUrl}/v1/dashboard`).catch(() => null),
        fetch(`${backendUrl}/v1/portfolio`).catch(() => null),
        fetch(`${backendUrl}/v1/bot`).catch(() => null),
        fetch(`${backendUrl}/v1/audit?limit=20`).catch(() => null),
        fetch(`${backendUrl}/v1/risk/evaluations?limit=20`).catch(() => null),
        fetch(`${backendUrl}/v1/tradingview/config`).catch(() => null),
      ]);

      if (healthRes && healthRes.ok) {
        setHealth(await healthRes.json());
      }
      if (dashboardRes && dashboardRes.ok) {
        setDashboard(await dashboardRes.json());
      }
      if (portfolioRes && portfolioRes.ok) {
        setPortfolio(await portfolioRes.json());
      }
      if (botsRes && botsRes.ok) {
        const data = await botsRes.json();
        if (Array.isArray(data)) {
          setBots(data.map((b: any) => ({
            id: b.bot_id || b.id,
            strategy_name: b.strategy_name || 'Unknown',
            symbol: b.symbol || '',
            status: typeof b.active === 'boolean' ? (b.active ? 'Running' : 'Stopped') : (b.state || 'Stopped'),
            execution_mode: 'Paper',
            last_error: b.last_error,
            last_tick_at: b.last_tick_at,
            signals_generated: b.signals_generated,
            orders_submitted: b.orders_submitted,
          })));
        } else if (data && typeof data === 'object') {
          const mapped: BotRecord = {
            id: data.bot_id || data.id || 'bot-1',
            strategy_name: data.config?.strategy_name || data.strategy_name || 'Unknown',
            symbol: data.config?.symbol || data.symbol || '',
            status: typeof data.active === 'boolean' ? (data.active ? 'Running' : 'Stopped') : (data.state || 'Stopped'),
            execution_mode: 'Paper',
            last_error: data.last_error,
            last_tick_at: data.last_tick_at,
            signals_generated: data.signals_generated,
            orders_submitted: data.orders_submitted,
          };
          setBots([mapped]);
        } else {
          setBots([]);
        }
      }
      if (logsRes && logsRes.ok) {
        setLogs(await logsRes.json());
      }
      if (riskRes && riskRes.ok) {
        setRiskEvaluations(await riskRes.json());
      }
      if (webhooksRes && webhooksRes.ok) {
        const data = await webhooksRes.json();
        const items = Array.isArray(data?.items) ? data.items : [];
        setWebhooks(items.map((item: any) => ({ symbol: item.symbol, exchange: item.exchange, created_at: item.created_at })));
      }
    } catch (e) {
      showToast('Failed to load admin data', 'error');
    } finally {
      setLoading(false);
    }
  }, [backendUrl, showToast]);

  useEffect(() => {
    fetchData();
    const intv = setInterval(fetchData, 30000);
    return () => clearInterval(intv);
  }, [fetchData]);

  const botControl = async (path: string, label: string) => {
    try {
      const res = await fetch(`${backendUrl}${path}`, { method: 'POST' });
      if (res.ok) {
        showToast(`${label} succeeded`, 'success');
        fetchData();
      } else {
        showToast(`${label} failed: ${res.status}`, 'error');
      }
    } catch {
      showToast(`${label} failed`, 'error');
    }
  };

  const emergencyStopAll = async () => {
    await botControl('/v1/bot/stop', 'Emergency stop');
    setBots((prev) => prev.map((b) => ({ ...b, status: 'Stopped', active: false })));
  };

  const renderOverview = () => (
    <div className="layout-grid animate-fade-in-up" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px' }}>
      <div className="glass-card layout-stats" style={{ gridColumn: 'span 2' }}>
        <h2 className="h3">System Health Overview</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginTop: '16px' }}>
          <div className="metric-card">
            <div className="text-muted">Status</div>
            <div className="h2" style={{ margin: '8px 0' }}>{health?.status || '—'}</div>
            <div className="text-muted" style={{ fontSize: '12px' }}>{health?.environment || ''}</div>
          </div>
          <div className="metric-card">
            <div className="text-muted">Execution Mode</div>
            <div className="h2" style={{ margin: '8px 0' }}>{health?.execution_mode || '—'}</div>
            <div className="text-muted" style={{ fontSize: '12px' }}>
              Live Trading: {typeof health?.live_trading_enabled === 'boolean' ? (health.live_trading_enabled ? 'Enabled' : 'Disabled') : '—'}
            </div>
          </div>
        </div>
        <div style={{ marginTop: '24px', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          {health?.services && Object.entries(health.services).map(([srv, ok]) => (
            <div key={srv} className={`badge ${ok ? 'badge-accent' : 'badge-danger'}`} style={{ padding: '8px 16px', fontSize: '14px', display: 'flex', gap: '8px', alignItems: 'center' }}>
              <StatusDot ok={!!ok} pulse={!!ok} /> {srv.toUpperCase()}
            </div>
          ))}
        </div>
      </div>

      <div className="glass-card-accent">
        <h2 className="h3">Dashboard Snapshot</h2>
        <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ padding: '16px', background: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <strong>Total Bots</strong>
              <span className="font-mono">{bots.length}</span>
            </div>
            <div className="text-muted" style={{ fontSize: '12px' }}>Active since last refresh</div>
          </div>
          <div style={{ padding: '16px', background: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <strong>Portfolio Equity</strong>
              <span className="font-mono">${(portfolio?.total_equity ?? 0).toFixed(2)}</span>
            </div>
            <div className="text-muted" style={{ fontSize: '12px' }}>Realized: ${(portfolio?.realized_pnl ?? 0).toFixed(2)}</div>
          </div>
          <div style={{ padding: '16px', background: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <strong>Kill Switch</strong>
              <span className={`badge ${health?.kill_switch_active ? 'badge-danger' : 'badge-accent'}`}>{health?.kill_switch_active ? 'ACTIVE' : 'INACTIVE'}</span>
            </div>
            <div className="text-muted" style={{ fontSize: '12px' }}>System-wide trading halt</div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderPerformance = () => (
    <div className="animate-fade-in-up">
      <div className="glass-card" style={{ marginBottom: '24px' }}>
        <h2 className="h3">Trading Performance Analytics</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px', marginTop: '16px' }}>
          <div className="metric-card">
            <div className="text-muted">Portfolio Equity</div>
            <div className="h2" style={{ color: 'var(--color-accent)', margin: '8px 0' }}>${(portfolio?.total_equity ?? 0).toFixed(2)}</div>
            <div className="text-muted font-mono" style={{ fontSize: '12px' }}>Cash: ${(portfolio?.cash ?? 0).toFixed(2)}</div>
          </div>
          <div className="metric-card">
            <div className="text-muted">Realized P&L</div>
            <div className="h2" style={{ color: (portfolio?.realized_pnl ?? 0) >= 0 ? 'var(--color-accent)' : 'var(--color-danger)', margin: '8px 0' }}>
              ${(portfolio?.realized_pnl ?? 0).toFixed(2)}
            </div>
            <div className="text-muted font-mono" style={{ fontSize: '12px' }}>Unrealized: ${(portfolio?.unrealized_pnl ?? 0).toFixed(2)}</div>
          </div>
          <div className="metric-card">
            <div className="text-muted">Positions Value</div>
            <div className="h2" style={{ margin: '8px 0' }}>${(portfolio?.positions_value ?? 0).toFixed(2)}</div>
            <div className="text-muted font-mono" style={{ fontSize: '12px' }}>Total equity includes cash</div>
          </div>
        </div>
      </div>
      <div className="glass-card">
        <h3 className="h3" style={{ marginBottom: '16px' }}>Recent Account Snapshots</h3>
        <div className="table-wrapper">
          <table className="table-base" style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Equity</th>
                <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Cash</th>
                <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Positions</th>
                <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Realized</th>
                <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Unrealized</th>
              </tr>
            </thead>
            <tbody>
              <tr className="table-tr" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td className="table-td font-mono" style={{ padding: '12px' }}>${(portfolio?.total_equity ?? 0).toFixed(2)}</td>
                <td className="table-td font-mono" style={{ padding: '12px' }}>${(portfolio?.cash ?? 0).toFixed(2)}</td>
                <td className="table-td font-mono" style={{ padding: '12px' }}>${(portfolio?.positions_value ?? 0).toFixed(2)}</td>
                <td className="table-td font-mono" style={{ padding: '12px' }}>${(portfolio?.realized_pnl ?? 0).toFixed(2)}</td>
                <td className="table-td font-mono" style={{ padding: '12px' }}>${(portfolio?.unrealized_pnl ?? 0).toFixed(2)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  const renderBots = () => (
    <div className="glass-card animate-fade-in-up">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h2 className="h3" style={{ margin: 0 }}>Bot Management Console</h2>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button className="btn-base btn-sm btn-ghost" onClick={fetchData}>Refresh</button>
          <button className="btn-base btn-sm btn-danger" onClick={emergencyStopAll}>Emergency Stop</button>
        </div>
      </div>
      <div className="table-wrapper">
        <table className="table-base" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
              <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>ID</th>
              <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Strategy</th>
              <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Symbol</th>
              <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Status</th>
              <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Signals</th>
              <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Orders</th>
              <th className="table-th" style={{ padding: '12px', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {bots.map((b) => (
              <tr key={b.id} className="table-tr" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td className="table-td font-mono" style={{ padding: '12px' }}>{b.id}</td>
                <td className="table-td" style={{ padding: '12px' }}>{b.strategy_name}</td>
                <td className="table-td" style={{ padding: '12px' }}>{b.symbol}</td>
                <td className="table-td" style={{ padding: '12px' }}>
                  <span className={`badge ${b.status === 'Running' || b.status === 'running' ? 'badge-accent' : b.status === 'Stopped' || b.status === 'stopped' ? 'badge-secondary' : 'badge-danger'}`}>
                    {b.status}
                  </span>
                </td>
                <td className="table-td" style={{ padding: '12px' }}>{b.signals_generated ?? 0}</td>
                <td className="table-td" style={{ padding: '12px' }}>{b.orders_submitted ?? 0}</td>
                <td className="table-td" style={{ padding: '12px', textAlign: 'right', display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                  <button className="btn-base btn-sm" onClick={() => botControl('/v1/bot/start', 'Start bot')}>Start</button>
                  <button className="btn-base btn-sm" onClick={() => botControl('/v1/bot/pause', 'Pause bot')}>Pause</button>
                  <button className="btn-base btn-sm" onClick={() => botControl('/v1/bot/resume', 'Resume bot')}>Resume</button>
                  <button className="btn-base btn-sm" onClick={() => botControl('/v1/bot/tick', 'Tick bot')}>Tick</button>
                  <button className="btn-base btn-sm btn-danger" onClick={() => botControl('/v1/bot/stop', 'Stop bot')}>Stop</button>
                </td>
              </tr>
            ))}
            {bots.length === 0 && (
              <tr><td className="table-td" style={{ padding: '16px', textAlign: 'center' }} colSpan={7}>No bots found</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderRisk = () => (
    <div className="layout-2col animate-fade-in-up" style={{ gap: '24px' }}>
      <div className="glass-card" style={{ borderColor: health?.kill_switch_active ? 'var(--color-danger)' : 'var(--border-card)', transition: 'all 0.3s' }}>
        <h2 className="h3" style={{ color: health?.kill_switch_active ? 'var(--color-danger)' : 'inherit' }}>Kill Switch</h2>
        <p className="text-muted" style={{ margin: '16px 0' }}>Immediately halts all trading activity, cancels open orders, and stops all bots.</p>
        <button
          className={`btn-base ${health?.kill_switch_active ? 'btn-danger' : 'btn-primary'}`}
          style={{ width: '100%', padding: '16px', fontSize: '18px', fontWeight: 'bold' }}
          onClick={async () => {
            await botControl('/v1/risk/kill-switch', 'Kill switch');
            fetchData();
          }}
        >
          {health?.kill_switch_active ? 'DEACTIVATE KILL SWITCH' : 'ACTIVATE KILL SWITCH'}
        </button>
      </div>

      <div className="glass-card">
        <h2 className="h3">Risk Evaluations</h2>
        <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {riskEvaluations.length === 0 && <div className="text-muted">No risk evaluations yet</div>}
          {riskEvaluations.slice(0, 20).map((r, idx) => {
            const rawTimestamp = r.created_at || r.timestamp;
            const safeTimestamp = rawTimestamp ? new Date(rawTimestamp).toLocaleString() : '—';
            return (
              <div key={r.id || idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)' }}>
                <div>
                  <strong style={{ fontSize: '14px' }}>{r.symbol || 'PORTFOLIO'}</strong>
                  <div style={{ marginTop: '4px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    <span className={`badge ${r.decision === 'APPROVED' ? 'badge-accent' : r.decision === 'REJECTED' ? 'badge-danger' : 'badge-secondary'}`}>{r.decision || 'PENDING'}</span>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="font-mono" style={{ fontSize: '14px' }}>{(r.quantity || 0).toFixed(4)}</div>
                  <div className="text-muted" style={{ fontSize: '11px' }}>{safeTimestamp}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );

  const renderHistory = () => (
    <div className="glass-card animate-fade-in-up">
      <h2 className="h3" style={{ marginBottom: '16px' }}>Audit Log & History</h2>
      <div className="table-wrapper">
        <table className="table-base" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
              <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Timestamp</th>
              <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Severity</th>
              <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Message</th>
            </tr>
          </thead>
          <tbody>
            {logs.slice(0, 50).map((l, idx) => (
              <tr key={l.id || idx} className="table-tr" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td className="table-td text-muted font-mono" style={{ fontSize: '13px', padding: '12px' }}>{new Date(l.timestamp || l.created_at || Date.now()).toLocaleString()}</td>
                <td className="table-td" style={{ padding: '12px' }}><SeverityBadge severity={l.severity} /></td>
                <td className="table-td" style={{ padding: '12px' }}>{l.message || l.event_type || 'Audit event'}</td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr><td className="table-td" style={{ padding: '16px', textAlign: 'center' }} colSpan={3}>No audit logs</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderWebhooks = () => (
    <div className="glass-card animate-fade-in-up">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h2 className="h3">TradingView Webhook Monitor</h2>
        <div style={{ display: 'flex', gap: '16px' }}>
          <span className="text-muted">Configs: <span style={{ color: 'var(--color-accent)' }}>{webhooks.length}</span></span>
        </div>
      </div>
      <div className="table-wrapper">
        <table className="table-base" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
              <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Symbol</th>
              <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Exchange</th>
              <th className="table-th" style={{ padding: '12px', textAlign: 'left' }}>Created</th>
            </tr>
          </thead>
          <tbody>
            {webhooks.map((w, idx) => (
              <tr key={w.symbol + (w.exchange || '') + idx} className="table-tr" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td className="table-td" style={{ padding: '12px', fontWeight: '500' }}>{w.symbol}</td>
                <td className="table-td" style={{ padding: '12px' }}>{w.exchange || 'default'}</td>
                <td className="table-td text-muted font-mono" style={{ fontSize: '13px', padding: '12px' }}>{w.created_at ? new Date(w.created_at).toLocaleString() : '—'}</td>
              </tr>
            ))}
            {webhooks.length === 0 && (
              <tr><td className="table-td" style={{ padding: '16px', textAlign: 'center' }} colSpan={3}>No webhook configs</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '32px 24px', minHeight: '100vh', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <style>{`
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        .dashboard-tab { padding: 12px 24px; border-radius: var(--radius-lg); font-weight: 600; cursor: pointer; transition: all 0.2s; color: var(--text-muted); background: transparent; border: none; font-size: 14px; }
        .dashboard-tab:hover { color: var(--text-primary); background: rgba(255,255,255,0.05); }
        .dashboard-tab.active { color: var(--color-primary-light); background: var(--color-primary-bg); border: 1px solid var(--color-primary-border); }
        .metric-bar-bg { height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; }
        .metric-bar-fill { height: 100%; transition: width 0.5s ease-out; }
      `}</style>

      {/* ── Quick Actions Toolbar ── */}
      <div className="glass-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
          <h1 className="h2 font-mono" style={{ margin: 0 }}>zksato Admin</h1>
          <div className="divider" style={{ width: '1px', height: '24px' }} />
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {(['overview', 'performance', 'bots', 'risk', 'history', 'webhooks'] as TabKey[]).map((tKey) => (
              <button key={tKey} className={`dashboard-tab ${tab === tKey ? 'active' : ''}`} onClick={() => setTab(tKey)}>
                {tKey.charAt(0).toUpperCase() + tKey.slice(1)}
              </button>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <button className="btn-base btn-ghost" onClick={fetchData}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '8px' }}><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/></svg>
            Refresh
          </button>
          <button className="btn-base btn-ghost" onClick={() => showToast('Report Exported', 'success')}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '8px' }}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
            Export
          </button>
          <button className="btn-base" style={{ background: 'rgba(255,255,255,0.1)' }} onClick={() => showToast('Mode toggle is informational in admin view', 'success')}>
            Live Mode
          </button>
          <button className="btn-base btn-danger" onClick={emergencyStopAll}>
            Emergency Stop
          </button>
        </div>
      </div>

      <div style={{ flex: 1 }}>
        {tab === 'overview' && renderOverview()}
        {tab === 'performance' && renderPerformance()}
        {tab === 'bots' && renderBots()}
        {tab === 'risk' && renderRisk()}
        {tab === 'history' && renderHistory()}
        {tab === 'webhooks' && renderWebhooks()}
      </div>

      {toast && <Toast msg={toast.msg} type={toast.type} />}
    </div>
  );
}
