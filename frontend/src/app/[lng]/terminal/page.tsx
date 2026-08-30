"use client";

import React, { useEffect, useRef, useState } from 'react';
import { getBackendUrl } from '../../../utils/api';

export default function TerminalPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loadError, setLoadError] = useState(false);
  const backendUrl = getBackendUrl();
  const terminalUrl = `${backendUrl}/v1/market/terminal`;

  useEffect(() => {
    // Inject TradingView widget script for direct browser rendering
    const scriptId = 'tradingview-widget-script';
    let script = document.getElementById(scriptId) as HTMLScriptElement | null;

    const initWidget = () => {
      if (containerRef.current && (window as any).TradingView) {
        containerRef.current.innerHTML = '';
        const widgetContainer = document.createElement('div');
        widgetContainer.id = 'tradingview_terminal_direct';
        widgetContainer.style.width = '100%';
        widgetContainer.style.height = '100%';
        containerRef.current.appendChild(widgetContainer);

        new (window as any).TradingView.widget({
          width: '100%',
          height: '100%',
          symbol: 'BINANCE:BTCUSDT',
          interval: '15',
          timezone: 'Asia/Bangkok',
          theme: 'dark',
          style: '1',
          locale: 'en',
          toolbar_bg: '#131722',
          enable_publishing: false,
          allow_symbol_change: true,
          container_id: 'tradingview_terminal_direct',
        });
      }
    };

    if (!script) {
      script = document.createElement('script');
      script.id = scriptId;
      script.src = 'https://s3.tradingview.com/tv.js';
      script.async = true;
      script.onload = initWidget;
      script.onerror = () => setLoadError(true);
      document.head.appendChild(script);
    } else if ((window as any).TradingView) {
      initWidget();
    } else {
      script.addEventListener('load', initWidget);
    }
  }, []);

  return (
    <div
      style={{
        width: '100%',
        height: 'calc(100vh - 80px)',
        background: '#131722',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Primary Direct Client-Side TradingView Widget */}
      <div
        ref={containerRef}
        style={{
          width: '100%',
          height: '100%',
          display: loadError ? 'none' : 'block',
        }}
      />

      {/* Fallback iFrame from Backend Market Terminal */}
      {loadError && (
        <iframe
          src={terminalUrl}
          title="TradingView Market Terminal"
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
            display: 'block',
          }}
        />
      )}
    </div>
  );
}
