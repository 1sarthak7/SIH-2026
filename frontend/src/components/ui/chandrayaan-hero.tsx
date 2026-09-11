"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { SilkAurora } from "@/components/ui/silk-aurora";

const navItems = [
  { label: "Home", href: "/" },
  { label: "Live Demo", href: "/demo" },
  { label: "Pipeline", href: "#pipeline" },
  { label: "About", href: "#about" },
  { label: "Contact", href: "#contact" },
];

const ChandrayaanHero = () => {
  return (
    <div className="h-screen w-full">
      <SilkAurora
        className="h-full min-h-0"
        speed={1}
        intensity={1}
        grain={0.85}
        mouseInfluence={1}
        vignette={1}
        baseColor="#030308"
        midColor="#0c0e1a"
        sheenColor="#d4c5a0"
        accentColor="#5b8def"
        subtitle="Chandrayaan-2 · ISRO · SIH 2026"
        title="Multi-Modal Lunar Feature Matching"
        description="AI-powered image correspondence system for Chandrayaan-2 satellite imagery. Finding matching features across OHRC, TMC-2 and IIRS instruments under varying sun angles and scale conditions."
      >
        {/* Nav */}
        <nav className="fixed left-1/2 top-0 z-50 -translate-x-1/2">
          <div
            className="flex items-center rounded-b-2xl px-4 py-2.5 sm:px-6 md:rounded-b-3xl md:px-8"
            style={{
              backgroundColor: "#000000",
              gap: "clamp(12px, 3vw, 56px)",
            }}
          >
            {navItems.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className="whitespace-nowrap text-[10px] text-white/60 transition-colors hover:text-white/90 sm:text-xs md:text-sm"
              >
                {item.label}
              </Link>
            ))}
          </div>
        </nav>

        {/* CTA Buttons */}
        <div className="flex items-center gap-4">
          <Link
            href="/demo"
            className="group inline-flex items-center gap-2 rounded-full bg-white py-1.5 pl-5 pr-1.5 text-sm font-medium text-black transition-all hover:gap-3 sm:text-base"
          >
            Live Demo
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-black transition-transform group-hover:scale-110 sm:h-9 sm:w-9">
              <ArrowRight className="h-4 w-4 text-white" />
            </span>
          </Link>
          <Link
            href="#pipeline"
            className="rounded-full border border-white/15 bg-white/5 px-5 py-2.5 text-sm font-medium text-white/60 transition-all hover:border-white/30 hover:text-white/80"
          >
            View Pipeline
          </Link>
        </div>
      </SilkAurora>
    </div>
  );
};

export { ChandrayaanHero };
