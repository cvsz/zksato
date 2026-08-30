"use client";

import React, { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { initI18n } from '../../i18n/client';
import { useTranslation } from 'react-i18next';
import { ThemeCustomizer } from '../../../components/settings/ThemeCustomizer';
import { AlertManager } from '../../../components/settings/TelegramLink';
import { NotificationPreferences } from '../../../components/settings/NotificationPreferences';
import { TradingViewConfig } from '../../../components/settings/TradingViewConfig';
import { getBackendUrl } from '../../../utils/api';

interface StatusMessage {
  type: 'success' | 'error';
  text: string;
}

export default function SettingsPage() {
  const pathname = usePathname();
  const lng = pathname?.split('/')[1] || 'en';
  initI18n(lng);
  const { t } = useTranslation('translation');

  const backendUrl = getBackendUrl();

  const [config, setConfig] = useState<Record<string, unknown> | null>(null);
  const [statusMessage, setStatusMessage] = useState<StatusMessage | null>(null);

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await fetch(`${backendUrl}/v1/config`);
        if (res.ok) {
          setConfig(await res.json());
        }
      } catch {
        // silent
      }
    };
    loadConfig();
  }, [backendUrl]);

  const renderMessage = (msg: StatusMessage | null) => {
    if (!msg) return null;
    return (
      <div
        role="alert"
        aria-live="polite"
        className={`badge ${msg.type === 'success' ? 'badge-accent' : 'badge-danger'}`}
        style={{
          display: 'flex',
          marginBottom: '16px',
          padding: '10px 14px',
          borderRadius: 'var(--radius-md)',
        }}
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          style={{ flexShrink: 0, marginRight: '8px' }}
        >
          {msg.type === 'success' ? (
            <polyline points="20 6 9 17 4 12" />
          ) : (
            <>
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </>
          )}
        </svg>
        <span>{msg.text}</span>
      </div>
    );
  };

  return (
    <div
      style={{
        maxWidth: '1280px',
        margin: '0 auto',
        padding: 'clamp(16px, 4vw, 40px) clamp(12px, 3vw, 24px)',
        minHeight: '90vh',
      }}
    >
      <h1
        className="h1"
        style={{
          marginBottom: '32px',
          paddingBottom: '16px',
          borderBottom: '1px solid var(--border-card)',
        }}
      >
        {t('settings.title')}
      </h1>

      <div className="layout-auto" style={{ gap: '28px' }}>
        <div style={{ display: 'grid', gap: '28px' }}>
          <div className="glass-card-static animate-fade-in">
            <h3 className="h3" style={{ marginBottom: '20px' }}>
              Server Configuration
            </h3>
            {config && (
              <div style={{ display: 'grid', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="text-muted">Environment</span>
                  <strong>{String(config.environment)}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="text-muted">Trading Mode</span>
                  <strong>{String(config.trading_mode)}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="text-muted">Live Trading</span>
                  <strong>{String(config.live_trading_enabled)}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="text-muted">Persistence</span>
                  <strong>{String(config.persistence_enabled ? 'PostgreSQL' : 'In-Memory')}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="text-muted">Reconciliation</span>
                  <strong>{String(config.reconciliation_ready)}</strong>
                </div>
              </div>
            )}
          </div>

          <AlertManager />
          <NotificationPreferences />
        </div>

        <div style={{ display: 'grid', gap: '28px' }}>
          <TradingViewConfig />
          <ThemeCustomizer />
        </div>
      </div>
    </div>
  );
}
