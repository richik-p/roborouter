import type { Metadata } from "next";
import Link from "next/link";
import { Cpu, GitCompareArrows, Radar } from "lucide-react";
import "@fontsource-variable/manrope";
import "@fontsource/ibm-plex-mono/400.css";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: "RoboRouter — Find the right policy for your robot",
  description: "Evidence-aware robot policy discovery, compatibility, evaluation, and Rollouts.",
  openGraph: {
    title: "Find what your robot can actually run.",
    description: "Evidence-aware robot policy discovery, compatibility, evaluation, and Rollouts.",
    siteName: "RoboRouter",
    type: "website",
    images: [{ url: "/og.png", width: 1731, height: 909, alt: "RoboRouter compatibility routing overview" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Find what your robot can actually run.",
    description: "Evidence-aware robot policy discovery and evaluation.",
    images: ["/og.png"],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="nav-shell">
          <Link href="/" className="brand" aria-label="RoboRouter home">
            <span className="brand-mark"><Radar size={19} strokeWidth={2.25} /></span>
            <span>ROBO<span>ROUTER</span></span>
          </Link>
          <nav aria-label="Main navigation">
            <Link href="/#explore">Explore</Link>
            <Link href="/compare"><GitCompareArrows size={15} /> Compare</Link>
            <Link href="/rollouts/rollout-upstream-pi05-libero-object"><Cpu size={15} /> Rollouts</Link>
          </nav>
          <Link href="/pilots" className="nav-cta">Become a pilot</Link>
        </header>
        <main>{children}</main>
        <footer>
          <div className="brand"><span className="brand-mark"><Radar size={16} /></span> ROBOROUTER</div>
          <p>Evidence before execution. Local authority before motion.</p>
          <span className="mono">PRE-BETA / v0.1</span>
        </footer>
      </body>
    </html>
  );
}
