"use client";

import React from 'react';
import { usePathname } from 'next/navigation';
import { Sidebar } from '../../components/layout/Sidebar';
import { Header } from '../../components/layout/Header';
import { SessionTimeoutModal } from '../../components/SessionTimeoutModal';

export default function LangLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const lng = pathname?.split('/')[1] || 'en';
  const isLoginPage = pathname?.includes('/login');

  return (
    <div lang={lng} className="tailadmin-root">
        <SessionTimeoutModal />
        <a
          href="#main-content"
          className="skip-link"
          style={{
            position: 'fixed',
            top: '-100%',
            left: '8px',
            zIndex: 10000,
            padding: '10px 16px',
            background: 'var(--color-primary)',
            color: '#fff',
            borderRadius: '0 0 8px 8px',
            fontSize: '14px',
            fontWeight: '600',
            textDecoration: 'none',
            transition: 'top 0.15s ease',
          }}
        >
          Skip to content
        </a>

        {isLoginPage ? (
          <main id="main-content" className="tailadmin-fullpage">
            {children}
          </main>
        ) : (
          <div className="tailadmin-layout">
              {/* Collapsible / Responsive Sidebar */}
              <Sidebar lng={lng} />

              {/* Content Area Column */}
              <div className="tailadmin-content-wrapper">
                {/* Sticky Header */}
                <Header lng={lng} />

                {/* Scrollable Main Viewport */}
                <main id="main-content" className="tailadmin-main">
                  <div className="tailadmin-container">
                    {children}
                  </div>
                </main>
              </div>
          </div>
        )}
    </div>
  );
}
