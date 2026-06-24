import type { Metadata } from "next";
import { Archivo, Inter, IBM_Plex_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const archivo = Archivo({ subsets: ["latin"], variable: "--font-archivo", weight: ["500", "600", "700"] });
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", weight: ["400", "500", "600"] });
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-plex-mono",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "sanctioned — lender-policy eligibility",
  description: "Deterministic, explainable home-loan matching across the lender panel.",
};

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/match", label: "Match" },
  { href: "/policy-diff", label: "Policy diff" },
  { href: "/ask", label: "Ask" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${archivo.variable} ${inter.variable} ${plexMono.variable}`}>
      <body>
        <header className="border-b border-line bg-surface">
          <div className="mx-auto flex max-w-[1280px] items-center gap-6 px-6 py-3">
            <Link href="/" className="font-display text-[15px] font-bold tracking-tight">
              sanctioned<span className="text-accent">.</span>
            </Link>
            <nav className="flex gap-1 text-sm">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-sm px-2.5 py-1 text-slate hover:bg-paper hover:text-ink"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
            <p className="ml-auto hidden text-[11px] leading-tight text-slate md:block">
              Indicative, public-sourced figures.
              <br />
              Not any lender&apos;s live or internal policy.
            </p>
          </div>
        </header>
        <main className="mx-auto max-w-[1280px] px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
