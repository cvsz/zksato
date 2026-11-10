"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { ThemeProvider } from "../contexts/ThemeContext";
import { SidebarProvider } from "../contexts/SidebarContext";
import { initI18n } from "./i18n/client";

const SUPPORTED_LOCALES = new Set(["en", "th", "zh", "ja"]);

export function AppProviders({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const segment = pathname?.split("/")[1] ?? "en";
  const locale = SUPPORTED_LOCALES.has(segment) ? segment : "en";

  // Initialize i18next before descendants render.
  initI18n(locale);

  return (
    <ThemeProvider>
      <SidebarProvider>{children}</SidebarProvider>
    </ThemeProvider>
  );
}
