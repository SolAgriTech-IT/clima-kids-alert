import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CLIMA-KIDS ALERT",
  description: "Alerte climatique pour la santé des enfants — Kolwezi, RDC",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <body className={`${inter.className} bg-brand-cream text-slate-900 dark:bg-slate-950 dark:text-slate-50`}>
        {children}
      </body>
    </html>
  );
}
