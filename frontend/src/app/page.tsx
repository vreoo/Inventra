"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRight,
  BarChart3,
  Brain,
  Menu,
  ShieldCheck,
  UploadCloud,
  X,
} from "lucide-react";
import SplitText from "@/components/SplitText";
import TargetCursor from "@/components/TargetCursor";
import SpotlightCard from "@/components/SpotlightCard";

type Feature = { title: string; description: string; icon: LucideIcon };

const features: Feature[] = [
  {
    title: "Guided Imports",
    description:
      "Upload spreadsheets or CSVs and let Inventra auto-map columns for you.",
    icon: UploadCloud,
  },
  {
    title: "Live Insights",
    description:
      "Track stock health, reorder risk, and forecast demand in real time.",
    icon: BarChart3,
  },
  {
    title: "AI Recommendations",
    description:
      "Surface pricing, bundling, and procurement suggestions powered by your data.",
    icon: Brain,
  },
];

const workflow = [
  {
    title: "Upload your inventory file",
    detail:
      "Drag and drop a CSV or connect your source of truth. We'll validate rows instantly.",
  },
  {
    title: "Review automated mappings",
    detail:
      "Confirm product identifiers, categories, and units with one-click suggestions.",
  },
  {
    title: "Publish and monitor",
    detail:
      "Push clean records to your systems and watch KPIs update in real time.",
  },
];

const navigationItems = [
  { href: "#features", label: "Features" },
  { href: "#workflow", label: "Workflow" },
];

export default function Home() {
  const [hasScrolled, setHasScrolled] = useState(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    const previousBehavior = root.style.scrollBehavior;
    root.style.scrollBehavior = "smooth";

    const handleScroll = () => {
      const currentY = window.scrollY;
      const scrolled = currentY > 12;

      setHasScrolled((prev) => (prev === scrolled ? prev : scrolled));
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      root.style.scrollBehavior = previousBehavior;
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setIsMobileNavOpen(false);
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return (
    <main className="relative isolate min-h-screen overflow-x-hidden bg-slate-950 text-slate-100">
      <TargetCursor spinDuration={4} hideDefaultCursor={true} />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.18),_transparent_60%)]" />
      <div className="pointer-events-none absolute -top-72 left-1/2 h-[500px] w-[500px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,_rgba(56,189,248,0.25)_0,_transparent_65%)] blur-3xl" />
      <div className="mx-auto flex  max-w-6xl flex-col px-6 pb-24 pt-10 ">
        <header>
          <nav className="sticky top-0 z-50 -mx-6 px-6 py-4 backdrop-blur bg-slate-950/80">
            <div
              className={cn(
                "mx-auto flex max-w-6xl flex-col gap-3",
                "transition-all duration-500",
                hasScrolled ? "shadow-lg shadow-slate-950/40" : "shadow-none"
              )}
            >
              <div className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-300">
                <Link
                  href="/"
                  className="cursor-target text-lg font-semibold tracking-tight text-white sm:text-xl"
                >
                  Inventra
                </Link>
                <div className="hidden items-center gap-6 lg:flex">
                  {navigationItems.map((item) => (
                    <a
                      key={item.href}
                      href={item.href}
                      className="cursor-target transition-colors hover:text-white"
                    >
                      {item.label}
                    </a>
                  ))}
                  <Button
                    asChild
                    size="sm"
                    variant="outline"
                    className="cursor-target border-white/15 bg-white/5 text-slate-100 transition-colors hover:bg-white/10"
                  >
                    <Link href="/upload">Upload</Link>
                  </Button>
                </div>
                <div className="flex items-center gap-2 lg:hidden">
                  <Button
                    asChild
                    size="sm"
                    variant="outline"
                    className="cursor-target border-white/15 bg-white/5 text-slate-100 transition-colors hover:bg-white/10"
                  >
                    <Link href="/upload">Upload</Link>
                  </Button>
                  <button
                    type="button"
                    aria-expanded={isMobileNavOpen}
                    aria-controls="primary-navigation"
                    onClick={() => setIsMobileNavOpen((prev) => !prev)}
                    className="cursor-target rounded-full border border-white/15 bg-white/5 p-2 text-slate-100 transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                  >
                    {isMobileNavOpen ? (
                      <X className="h-5 w-5" />
                    ) : (
                      <Menu className="h-5 w-5" />
                    )}
                    <span className="sr-only">
                      {isMobileNavOpen ? "Close navigation" : "Open navigation"}
                    </span>
                  </button>
                </div>
              </div>
              <div
                id="primary-navigation"
                className={cn(
                  "lg:hidden",
                  "rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 text-sm text-slate-200 transition-all duration-200",
                  isMobileNavOpen
                    ? "pointer-events-auto translate-y-0 opacity-100"
                    : "pointer-events-none -translate-y-2 opacity-0"
                )}
              >
                <div className="flex flex-col gap-3">
                  {navigationItems.map((item) => (
                    <a
                      key={item.href}
                      href={item.href}
                      onClick={() => setIsMobileNavOpen(false)}
                      className="cursor-target rounded-lg px-2 py-2 transition-colors hover:bg-white/10 hover:text-white"
                    >
                      {item.label}
                    </a>
                  ))}
                  <Button
                    asChild
                    size="sm"
                    className="cursor-target bg-cyan-400 text-slate-950 shadow-lg shadow-cyan-400/30 transition-transform hover:translate-y-0.5 hover:bg-cyan-300"
                    onClick={() => setIsMobileNavOpen(false)}
                  >
                    <Link href="/upload">Start uploading</Link>
                  </Button>
                </div>
              </div>
            </div>
          </nav>
        </header>
        <section className="mt-16 grid gap-12 lg:grid-cols-[1.1fr,0.9fr] lg:items-center">
          <div className="space-y-7">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-slate-300">
              Predictable inventory, without the busywork
            </span>
            <div className="space-y-6">
              <SplitText
                text="Give your operations a single source of truth."
                className="text-4xl font-semibold leading-tight text-white sm:text-5xl md:text-6xl"
                duration={0.8}
                delay={200}
                splitType="words"
                ease="power3.out"
                onLetterAnimationComplete={() => {}}
              />
              <p className="max-w-xl text-base text-slate-300 sm:text-lg">
                Inventra harmonizes uploads, validation, and analytics so your
                team can make confident fulfillment decisions. Upload data once,
                share insights everywhere.
              </p>
            </div>
            <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
              <Button
                asChild
                size="lg"
                className="w-full cursor-target group bg-cyan-400 text-slate-950 shadow-lg shadow-cyan-400/30 transition-transform hover:translate-y-0.5 hover:bg-cyan-300 sm:w-auto"
              >
                <Link href="/upload" className="w-full text-center">
                  Start uploading
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="ghost"
                className="w-full cursor-target text-slate-300 hover:text-black sm:w-auto"
              >
                <a href="#features" className="w-full text-center">
                  Explore features
                </a>
              </Button>
            </div>
            <ul className="mt-6 grid gap-2 text-sm text-slate-300">
              <li className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                Automated schema detection with instant feedback
              </li>
              <li className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                Real-time alerts for low stock and cost anomalies
              </li>
              <li className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                Built for teams—share views and approvals in one place
              </li>
            </ul>
          </div>

          <SpotlightCard
            className={cn(
              "cursor-target h-full bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.10),_rgba(15,23,42,1)_80%)] p-6 sm:p-8"
            )}
            spotlightColor="rgba(255, 255, 255, 0.2)"
          >
            <div className="flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-white/5 p-5 text-sm text-slate-200">
              <div>
                <p className="text-xs uppercase tracking-wider text-slate-400">
                  Next upload
                </p>
                <p className="mt-1 text-base font-medium text-white">
                  inventory_q1.csv
                </p>
              </div>
              <span className="rounded-full border border-emerald-400/40 bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-300">
                Ready
              </span>
            </div>
            <div className="mt-8 grid gap-5 text-sm text-slate-300">
              {workflow.map((item, index) => (
                <div key={item.title} className="flex items-start gap-4">
                  <div className="flex size-8 items-center justify-center rounded-full border border-white/10 bg-white/5 text-xs font-semibold text-cyan-300">
                    {index + 1}
                  </div>
                  <div>
                    <p className="font-medium text-white">{item.title}</p>
                    <p className="mt-1 text-slate-300">{item.detail}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-8 flex items-center justify-between rounded-2xl border border-white/10 bg-gradient-to-r from-white/5 via-transparent to-white/5 p-5">
              <div>
                <p className="text-xs uppercase tracking-wider text-slate-400">
                  Forecast snapshot
                </p>
                <p className="mt-1 text-lg font-semibold text-white">
                  98.7% fill rate
                </p>
              </div>
              <div className="text-right text-xs text-slate-400">
                <p>Lead time savings</p>
                <p className="text-sm font-semibold text-cyan-300">-32%</p>
              </div>
            </div>
          </SpotlightCard>
        </section>

        <section id="features" className="mt-20 md:mt-24">
          <div className="max-w-2xl space-y-4">
            <h2 className="text-3xl font-semibold text-white sm:text-4xl">
              Everything you need to stay in sync
            </h2>
            <p className="text-base text-slate-300">
              Inventra is crafted for growing teams who want clarity without the
              operational drag. Each workflow is grounded in real inventory
              habits—no extra toggles, just what helps you move faster.
            </p>
          </div>
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <FeatureCard key={feature.title} feature={feature} />
            ))}
          </div>
        </section>

        <section id="workflow" className="mt-20 md:mt-24">
          <SpotlightCard
            className={cn(
              "cursor-target h-full bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.10),_rgba(15,23,42,1)_80%)] p-6 sm:p-8"
            )}
            spotlightColor="rgba(255, 255, 255, 0.2)"
          >
            <div className="grid gap-10 md:grid-cols-[0.65fr,1fr] md:items-center">
              <div className="space-y-4">
                <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">
                  Upload in minutes
                </p>
                <h3 className="text-2xl font-semibold text-white sm:text-3xl">
                  From messy spreadsheets to trusted dashboards.
                </h3>
                <p className="text-sm text-slate-300">
                  Borrowing from Reactbits motion principles, we keep the
                  interface lively while focusing attention on what matters—the
                  path from raw data to action. Every step is transparent so you
                  always know what comes next.
                </p>
              </div>
              <ul className="grid gap-6 text-sm text-slate-300">
                {workflow.map((item, index) => (
                  <li key={item.title} className="flex gap-4">
                    <div className="mt-1 flex size-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-sm font-semibold text-cyan-300">
                      {index + 1}
                    </div>
                    <div>
                      <p className="font-medium text-white">{item.title}</p>
                      <p className="mt-1">{item.detail}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
            <div className="mt-10 flex flex-col items-start gap-3 border-t border-white/10 pt-8 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-slate-300">
                Ready to experience it? Upload your current inventory snapshot
                and watch insights populate instantly.
              </p>
              <Button
                asChild
                size="lg"
                className="cursor-target group bg-white text-slate-950 hover:bg-slate-200"
              >
                <Link href="/upload">
                  Go to upload
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </Link>
              </Button>
            </div>
          </SpotlightCard>
        </section>
      </div>
    </main>
  );
}

function FeatureCard({ feature }: { feature: Feature }) {
  const Icon = feature.icon;

  return (
    <SpotlightCard
      className={cn(
        "cursor-target h-full bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.10),_rgba(15,23,42,1)_80%)] p-6 sm:p-7 lg:p-8"
      )}
      spotlightColor="rgba(255, 255, 255, 0.2)"
    >
      <div className="flex size-12 items-center justify-center rounded-xl border border-white/10 bg-white/10 text-cyan-300">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="mt-6 text-lg font-semibold text-white">{feature.title}</h3>
      <p className="mt-3 text-sm text-slate-300">{feature.description}</p>
    </SpotlightCard>
  );
}
