"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * SVG filter for liquid glass refraction.
 * Displacement creates visible light-bending through the glass.
 */
function LiquidGlassFilter() {
  return (
    <svg className="hidden" aria-hidden="true" style={{ position: "absolute", width: 0, height: 0 }}>
      <defs>
        <filter
          id="liquid-glass-nav"
          x="-25%"
          y="-25%"
          width="150%"
          height="150%"
          colorInterpolationFilters="sRGB"
        >
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.008 0.012"
            numOctaves={3}
            seed={7}
            result="noise"
          />
          <feGaussianBlur in="noise" stdDeviation={6} result="smoothNoise" />
          <feDisplacementMap
            in="SourceGraphic"
            in2="smoothNoise"
            scale={45}
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
      </defs>
    </svg>
  );
}

interface LiquidGlassNavProps {
  children: React.ReactNode;
  className?: string;
}

export function LiquidGlassNav({ children, className }: LiquidGlassNavProps) {
  return (
    <>
      <nav
        className={cn(
          "relative overflow-hidden rounded-b-2xl md:rounded-b-3xl",
          className
        )}
      >
        {/* Refraction layer */}
        <div
          className="absolute inset-0 z-0 rounded-b-2xl md:rounded-b-3xl"
          style={{
            backdropFilter: "saturate(1.4) brightness(1.05) contrast(1.05)",
            WebkitBackdropFilter: "saturate(1.4) brightness(1.05) contrast(1.05)",
            filter: "url(#liquid-glass-nav)",
          }}
        />

        {/* Glass rim highlights */}
        <div
          className={cn(
            "absolute inset-0 z-[1] rounded-b-2xl md:rounded-b-3xl pointer-events-none",
            "shadow-[inset_0_1px_1px_rgba(255,255,255,0.2),inset_0_-1px_1px_rgba(0,0,0,0.3),inset_2px_2px_4px_rgba(255,255,255,0.06),inset_-2px_-2px_4px_rgba(0,0,0,0.15),0_0_12px_rgba(0,0,0,0.2)]"
          )}
        />

        {/* Top specular highlight */}
        <div className="absolute inset-x-4 top-[2px] z-[2] h-[40%] rounded-full bg-gradient-to-b from-white/10 to-transparent pointer-events-none" />

        {/* Subtle tint */}
        <div className="absolute inset-0 z-[1] rounded-b-2xl md:rounded-b-3xl bg-white/[0.03] pointer-events-none" />

        {/* Content */}
        <div className="relative z-10">{children}</div>
      </nav>
      <LiquidGlassFilter />
    </>
  );
}
