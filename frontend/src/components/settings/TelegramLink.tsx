"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { getBackendUrl } from '../../utils/api';

interface AlertRule {
  id: string;
  symbol: string;
  condition: string;
  price: number;
  created_at: string;
}

export function AlertManager() {
  const { t } = useTranslation();
  const [alerts, setAlerts] = useState<AlertRule[]>([]);
  const [symbol, setSymbol] = useState('');
  const [condition, setCondition] = useState('gte');
  const [price, setPrice] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  const backendUrl = getBackendUrl();

  const loadAlerts = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/v1/alerts`);
      if (res.ok) {
        const data = await res.json();
        setAlerts(data);
      }
    } catch {
      // silent
    }
  }, [backendUrl]);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch(`${backendUrl}/v1/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: symbol.toUpperCase(),
          condition,
          price: Number(price),
        }),
      });
      if (res.ok) {
        setMessage({ type: 'success', text: 'Alert created' });
        setSymbol('');
        setPrice('');
        loadAlerts();
      } else {
        const err = await res.json().catch(() => ({}));
        setMessage({ type: 'error', text: err.detail || 'Failed to create alert' });
      }
    } catch {
      setMessage({ type: 'error', text: 'Failed to create alert' });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const res = await fetch(`${backendUrl}/v1/alerts/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setAlerts((prev) => prev.filter((a) => a.id !== id));
      }
    } catch {
      // silent
    }
  };

  return (
    <div className="glass-card-static animate-fade-in">
      <h3 className="h3" style={{ marginBottom: '20px' }}>
        Price Alerts
      </h3>

      <form onSubmit={handleCreate} style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ flex: 1, minWidth: '120px', marginBottom: 0 }}>
            <label className="form-label">Symbol</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="AOT"
              className="input-field"
              required
            />
          </div>
          <div className="form-group" style={{ flex: 1, minWidth: '120px', marginBottom: 0 }}>
            <label className="form-label">Condition</label>
            <select
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
              className="input-field"
            >
              <option value="gte">Greater or equal</option>
              <option value="lte">Less or equal</option>
            </select>
          </div>
          <div className="form-group" style={{ flex: 1, minWidth: '120px', marginBottom: 0 }}>
            <label className="form-label">Price</label>
            <input
              type="number"
              step="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="0.00"
              className="input-field"
              required
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button type="submit" disabled={loading} className="btn-base btn-primary">
              {loading ? 'Saving...' : 'Add Alert'}
            </button>
          </div>
        </div>
      </form>

      {message && (
        <div
          role="alert"
          className={`badge ${message.type === 'success' ? 'badge-accent' : 'badge-danger'}`}
          style={{
            display: 'flex',
            marginBottom: '16px',
            padding: '10px 14px',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <span>{message.text}</span>
        </div>
      )}

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
            <button
              onClick={() => handleDelete(alert.id)}
              className="btn-base btn-danger btn-sm"
            >
              Remove
            </button>
          </div>
        ))}
        {alerts.length === 0 && (
          <div className="text-muted" style={{ textAlign: 'center', padding: '16px' }}>
            No alerts configured
          </div>
        )}
      </div>
    </div>
  );
}
