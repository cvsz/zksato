"use client";

import React from 'react';
import { getBackendUrl } from '../../../utils/api';

export default function TerminalPage() {
  const backendUrl = getBackendUrl();
  const terminalUrl = `${backendUrl}/v1/market/terminal`;

  return (
    <div style={{ width: '100%', height: 'calc(100vh - 80px)', background: '#131722', position: 'relative' }}>
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
    </div>
  );
}
