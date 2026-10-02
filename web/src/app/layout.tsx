import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Saira } from "next/font/google";

import { Providers } from "@/components/providers";
import { BottomNav, SideRail } from "@/components/shell/nav";
import { TopBar } from "@/components/shell/top-bar";

import "./globals.css";

// Three families total (§2.4): Geist (UI), Geist Mono (codes/overs), Saira (display/scores).
const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });
// Saira is variable in wght 100–900 and wdth 50–125; `axes: ["wdth"]` ships the width axis so
// `font-stretch: 75% / 87.5%` gives the condensed scoreboard voice from one file.
const saira = Saira({ variable: "--font-saira", subsets: ["latin"], axes: ["wdth"], display: "swap" });

export const metadata: Metadata = {
  title: { default: "Predict-11", template: "%s · Predict-11" },
  description: "IPL Dream11 fantasy-XI projections with honest uncertainty.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F5F6FA" },
    { media: "(prefers-color-scheme: dark)", color: "#0B0E1C" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} ${saira.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        <Providers>
          <a
            href="#main"
            className="sr-only z-50 rounded-md bg-surface-3 px-3 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:ring-2 focus:ring-ring"
          >
            Skip to content
          </a>
          <TopBar />
          <div className="flex">
            <SideRail />
            <main
              id="main"
              className="mx-auto w-full max-w-[1680px] min-w-0 flex-1 px-4 pt-5 pb-[calc(6rem+env(safe-area-inset-bottom))] md:px-6 lg:pb-12"
            >
              {children}
            </main>
          </div>
          <BottomNav />
        </Providers>
      </body>
    </html>
  );
}
