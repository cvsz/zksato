"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';

interface AlertRule {
  id: string;
  symbol: string;
  condition: string;
  price: number;
  created_at: string;
}

export function NotificationPreferences() {
  const { t } = useTranslation();
  const [alerts, setAlerts] = useState<AlertRule[]>([]);

  const backendUrl =
    process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:9569';

  const loadAlerts = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/v1/alerts`);
      if (res.ok) {
        setAlerts(await res.json());
      }
    } catch {
      // silent
    }
  }, [backendUrl]);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  return (
    <div className="glass-card-static animate-fade-in">
      <h3 className="h3" style={{ marginBottom: '20px' }}>
        Active Alerts
      </h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {alerts.map((alert) => (
          <div
            key={alert.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <div>
              <strong style={{ marginRight: '8px' }}>{alert.symbol}</strong>
              <span className="text-muted">
                {alert.condition === 'gte' ? '≥' : '≤'} {alert.price}
              </span>
            </div>
            <span className="text-secondary" style={{ fontSize: '12px' }}>
              {new Date(alert.created_at).toLocaleString()}
            </span>
          </div>
        ))}
        {alerts.length === 0 && (
          <div className="text-muted" style={{ textAlign: 'center', padding: '16px' }}>
            No active alerts
          </div>
        )}
      </div>
    </div>
  );
}
