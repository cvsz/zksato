"use client";

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { useSidebar } from '../../contexts/SidebarContext';
import { useTheme } from '../../contexts/ThemeContext';
import { LanguageSelector } from '../LanguageSelector';
import { getBackendUrl, getAuthHeaders } from '../../utils/api';

interface HeaderProps {
  lng: string;
}

export function Header({ lng }: HeaderProps) {
  const router = useRouter();
  const { t } = useTranslation();
  const { toggleSidebar } = useSidebar();
  const { theme, setTheme } = useTheme();

  const [systemHealth, setSystemHealth] = useState<'healthy' | 'degraded' | 'offline'>('healthy');
  const [tradingMode, setTradingMode] = useState<string>('paper');
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [userRole, setUserRole] = useState<string>('guest');
  const [userSubject, setUserSubject] = useState<string>('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Poll system status for the header status pill
  useEffect(() => {
    let active = true;
    const fetchStatus = async () => {
      try {
        const backend = getBackendUrl();
        const res = await fetch(`${backend}/health`, { signal: AbortSignal.timeout(4000) });
        if (!active) return;
        if (res.ok) {
          const data = await res.json();
          setSystemHealth(data.status === 'ok' ? 'healthy' : 'degraded');
          setTradingMode(data.mode || 'paper');
        } else {
          setSystemHealth('degraded');
        }
      } catch {
        if (active) setSystemHealth('offline');
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 8000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // Fetch current user credentials
  useEffect(() => {
    let active = true;
    const checkAuth = async () => {
      try {
        const backend = getBackendUrl();
        const res = await fetch(`${backend}/v1/auth/me`, {
          headers: getAuthHeaders(),
          signal: AbortSignal.timeout(4000),
        });
        if (!active) return;
        if (res.ok) {
          const data = await res.json();
          setUserRole(data.role || 'operator');
          setUserSubject(data.subject || 'authenticated');
        }
      } catch {
        // keep fallback
      }
    };
    checkAuth();
    return () => { active = false; };
  }, []);

  // Click outside to close user dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setUserDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    try {
      await fetch('/v1/auth/session', { method: 'DELETE' }).catch(() => {});
    } finally {
      sessionStorage.removeItem('zksato_api_key');
      sessionStorage.removeItem('auth_user');
      router.push(`/${lng}/login`);
    }
  };

  return (
    <header className="tailadmin-header">
      {/* Left: Mobile Sidebar Hamburger */}
      <div className="tailadmin-header-left">
        <button
          onClick={toggleSidebar}
          className="tailadmin-hamburger-btn"
          aria-label="Toggle sidebar"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>

        {/* System Status Indicator Pill */}
        <div className="tailadmin-status-pill" title={`Engine Status: ${systemHealth.toUpperCase()}`}>
          <span className={`status-dot ${systemHealth}`} />
          <span className="status-label">
            Engine: <strong>{systemHealth === 'healthy' ? 'ACTIVE' : systemHealth.toUpperCase()}</strong>
          </span>
          <span className="status-divider">•</span>
          <span className={`mode-badge mode-${tradingMode.toLowerCase()}`}>
            {tradingMode.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Right: Quick actions, Theme, Lang, User */}
      <div className="tailadmin-header-right">
        {/* Theme Toggle Button */}
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="tailadmin-icon-btn"
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          aria-label="Toggle Theme"
        >
          {theme === 'dark' ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="5" />
              <line x1="12" y1="1" x2="12" y2="3" />
              <line x1="12" y1="21" x2="12" y2="23" />
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
              <line x1="1" y1="12" x2="3" y2="12" />
              <line x1="21" y1="12" x2="23" y2="12" />
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          )}
        </button>

        {/* Language Selector Dropdown */}
        <div className="tailadmin-lang-wrap">
          <LanguageSelector />
        </div>

        {/* User Profile Menu Dropdown */}
        <div className="tailadmin-user-dropdown" ref={dropdownRef}>
          <button
            onClick={() => setUserDropdownOpen((prev) => !prev)}
            className="tailadmin-user-btn"
            aria-expanded={userDropdownOpen}
          >
            <div className="user-avatar">
              <span>{userRole.charAt(0).toUpperCase()}</span>
            </div>
            <div className="user-meta">
              <span className="user-name">{userRole.replace('_', ' ')}</span>
              <span className="user-sub">{userSubject ? userSubject.slice(0, 16) : 'Verified Operator'}</span>
            </div>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          {userDropdownOpen && (
            <div className="tailadmin-dropdown-menu">
              <div className="dropdown-header">
                <span className="dropdown-title">Operator Profile</span>
                <span className="dropdown-badge">{userRole}</span>
              </div>
              <div className="dropdown-divider" />
              <Link
                href={`/${lng}/settings`}
                onClick={() => setUserDropdownOpen(false)}
                className="dropdown-item"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
                <span>{t('menu.settings') || 'Settings'}</span>
              </Link>
              <Link
                href={`/${lng}/admin`}
                onClick={() => setUserDropdownOpen(false)}
                className="dropdown-item"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                <span>{t('menu.admin') || 'Admin Panel'}</span>
              </Link>
              <div className="dropdown-divider" />
              <button
                onClick={handleLogout}
                className="dropdown-item danger"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                <span>{t('menu.logout') || 'Sign Out'}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
