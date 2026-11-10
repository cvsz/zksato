"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { useSidebar } from '../../contexts/SidebarContext';

interface SidebarProps {
  lng: string;
}

interface NavItem {
  key: string;
  i18nKey: string;
  label: string;
  path: string;
  badge?: string;
  icon: React.ReactNode;
}

interface NavGroup {
  groupName: string;
  items: NavItem[];
}

export function Sidebar({ lng }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useTranslation();
  const { sidebarOpen, setSidebarOpen, isCollapsed, toggleCollapse } = useSidebar();

  const handleLogout = async () => {
    try {
      await fetch('/v1/auth/session', { method: 'DELETE' }).catch(() => {});
    } finally {
      sessionStorage.removeItem('zksato_api_key');
      sessionStorage.removeItem('auth_user');
      router.push(`/${lng}/login`);
    }
  };

  const navGroups: NavGroup[] = [
    {
      groupName: 'Trading Control',
      items: [
        {
          key: 'dashboard',
          i18nKey: 'menu.dashboard',
          label: 'Overview & Risk',
          path: 'dashboard',
          icon: (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
            </svg>
          ),
        },
        {
          key: 'terminal',
          i18nKey: 'menu.terminal',
          label: 'Order Terminal',
          path: 'terminal',
          icon: (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="4 17 10 11 4 5" />
              <line x1="12" y1="19" x2="20" y2="19" />
            </svg>
          ),
        },
        {
          key: 'reconciliation',
          i18nKey: 'menu.reconciliation',
          label: 'Reconciliation',
          path: 'reconciliation',
          icon: (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
              <path d="M3 3v5h5" />
              <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
              <path d="M16 21h5v-5" />
            </svg>
          ),
        },
      ],
    },
    {
      groupName: 'Derivatives & Research',
      items: [
        {
          key: 'tfex',
          i18nKey: 'menu.tfex',
          label: 'TFEX Futures',
          path: 'tfex',
          badge: 'SET/TFEX',
          icon: (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 3v18h18" />
              <path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3" />
            </svg>
          ),
        },
        {
          key: 'research',
          i18nKey: 'menu.research',
          label: 'AI & Video EA',
          path: 'research',
          badge: 'AI',
          icon: (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
              <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
            </svg>
          ),
        },
      ],
    },
    {
      groupName: 'Platform & Admin',
      items: [
        {
          key: 'admin',
          i18nKey: 'menu.admin',
          label: 'Control Panel',
          path: 'admin',
          icon: (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          ),
        },
        {
          key: 'settings',
          i18nKey: 'menu.settings',
          label: 'System Settings',
          path: 'settings',
          icon: (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          ),
        },
      ],
    },
  ];

  const currentSegment = pathname?.split('/')[2] || 'dashboard';

  return (
    <>
      {/* Mobile Backdrop */}
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          className="tailadmin-backdrop"
          aria-hidden="true"
        />
      )}

      {/* TailAdmin Sidebar Shell */}
      <aside
        className={`tailadmin-sidebar ${sidebarOpen ? 'open' : ''} ${isCollapsed ? 'collapsed' : ''}`}
        aria-label="Sidebar Navigation"
      >
        {/* Brand Header */}
        <div className="tailadmin-sidebar-header">
          <Link href={`/${lng}/dashboard`} className="tailadmin-logo-wrapper">
            <div className="tailadmin-logo-mark">
              <div className="tailadmin-logo-dot" />
            </div>
            {!isCollapsed && (
              <div className="tailadmin-brand-text">
                <span className="brand-title">z<span className="brand-accent">ksato</span></span>
                <span className="brand-subtitle">Risk-First Trading</span>
              </div>
            )}
          </Link>

          {/* Desktop Collapse Toggle */}
          <button
            onClick={toggleCollapse}
            className="tailadmin-collapse-btn"
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ transform: isCollapsed ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s ease' }}
            >
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
        </div>

        {/* Navigation Sections */}
        <div className="tailadmin-sidebar-nav">
          {navGroups.map((group) => (
            <div key={group.groupName} className="tailadmin-nav-group">
              {!isCollapsed && (
                <div className="tailadmin-group-label">
                  {group.groupName}
                </div>
              )}
              <ul className="tailadmin-nav-list">
                {group.items.map((item) => {
                  const isActive = currentSegment === item.path;
                  return (
                    <li key={item.key}>
                      <Link
                        href={`/${lng}/${item.path}`}
                        onClick={() => setSidebarOpen(false)}
                        className={`tailadmin-nav-link ${isActive ? 'active' : ''}`}
                        title={isCollapsed ? (t(item.i18nKey) || item.label) : undefined}
                      >
                        <span className="tailadmin-nav-icon">{item.icon}</span>
                        {!isCollapsed && (
                          <>
                            <span className="tailadmin-nav-text">
                              {t(item.i18nKey) || item.label}
                            </span>
                            {item.badge && (
                              <span className="tailadmin-nav-badge">
                                {item.badge}
                              </span>
                            )}
                          </>
                        )}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        {/* Sidebar Footer User & Status */}
        <div className="tailadmin-sidebar-footer">
          <button
            onClick={handleLogout}
            className="tailadmin-logout-btn"
            title={isCollapsed ? 'Sign Out' : undefined}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            {!isCollapsed && <span>{t('menu.logout') || 'Sign Out'}</span>}
          </button>
        </div>
      </aside>
    </>
  );
}
