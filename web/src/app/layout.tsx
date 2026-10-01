import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { Providers } from "@/components/providers";
import { BottomNav, SideNav } from "@/components/shell/nav";
import { TopBar } from "@/components/shell/top-bar";

import "./globals.css";

const geistSans = Geist({ variable: "--font-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Predict-11", template: "%s · Predict-11" },
  description: "IPL Dream11 fantasy-XI projections with honest uncertainty.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" suppressHydrationWarning className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full">
        <Providers>
          <a
            href="#main"
            className="sr-only z-50 rounded-md bg-background px-3 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:ring-3 focus:ring-ring/50"
          >
            Skip to content
          </a>
          <TopBar />
          <div className="flex">
            <SideNav />
            <main id="main" className="min-w-0 flex-1 px-4 pt-4 pb-24 md:px-6 md:pb-8">
              {children}
            </main>
          </div>
          <BottomNav />
        </Providers>
      </body>
    </html>
  );
}
