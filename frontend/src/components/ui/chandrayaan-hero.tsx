"use client";

import { motion, useInView } from "framer-motion";
import { ArrowRight, Satellite, Microscope, Globe2, Sparkles } from "lucide-react";
import { useRef } from "react";
import Link from "next/link";

/* ---------------- WordsPullUp ---------------- */
interface WordsPullUpProps {
  text: string;
  className?: string;
  showAsterisk?: boolean;
  style?: React.CSSProperties;
}

export const WordsPullUp = ({ text, className = "", showAsterisk = false, style }: WordsPullUpProps) => {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true });
  const words = text.split(" ");

  return (
    <div ref={ref} className={`inline-flex flex-wrap ${className}`} style={style}>
      {words.map((word, i) => {
        const isLast = i === words.length - 1;
        return (
          <motion.span
            key={i}
            initial={{ y: 20, opacity: 0 }}
            animate={isInView ? { y: 0, opacity: 1 } : {}}
            transition={{ duration: 0.6, delay: i * 0.08, ease: [0.16, 1, 0.3, 1] }}
            className="inline-block relative"
            style={{ marginRight: isLast ? 0 : "0.25em" }}
          >
            {word}
            {showAsterisk && isLast && (
              <span className="absolute top-[0.65em] -right-[0.3em] text-[0.31em]">*</span>
            )}
          </motion.span>
        );
      })}
    </div>
  );
};

/* ---------------- WordsPullUpMultiStyle ---------------- */
interface Segment {
  text: string;
  className?: string;
}

interface WordsPullUpMultiStyleProps {
  segments: Segment[];
  className?: string;
  style?: React.CSSProperties;
}

export const WordsPullUpMultiStyle = ({ segments, className = "", style }: WordsPullUpMultiStyleProps) => {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true });

  const words: { word: string; className?: string }[] = [];
  segments.forEach((seg) => {
    seg.text.split(" ").forEach((w) => {
      if (w) words.push({ word: w, className: seg.className });
    });
  });

  return (
    <div ref={ref} className={`inline-flex flex-wrap justify-center ${className}`} style={style}>
      {words.map((w, i) => (
        <motion.span
          key={i}
          initial={{ y: 20, opacity: 0 }}
          animate={isInView ? { y: 0, opacity: 1 } : {}}
          transition={{ duration: 0.6, delay: i * 0.08, ease: [0.16, 1, 0.3, 1] }}
          className={`inline-block ${w.className ?? ""}`}
          style={{ marginRight: "0.25em" }}
        >
          {w.word}
        </motion.span>
      ))}
    </div>
  );
};

/* ---------------- Chandrayaan Hero ---------------- */
const navItems = [
  { label: "Home", href: "/" },
  { label: "Live Demo", href: "/demo" },
  { label: "Pipeline", href: "#pipeline" },
  { label: "About", href: "#about" },
];

const statsItems = [
  { icon: Microscope, value: "0.25m", label: "Resolution" },
  { icon: Satellite, value: "LoFTR", label: "AI Model" },
  { icon: Globe2, value: "Sub-px", label: "Accuracy" },
  { icon: Sparkles, value: "~50s", label: "Processing" },
];

const ChandrayaanHero = () => {
  return (
    <section className="h-screen w-full">
      <div className="relative h-full w-full overflow-hidden rounded-2xl md:rounded-[2rem]">

        {/* Background — lunar surface image */}
        <div
          className="absolute inset-0 h-full w-full"
          style={{
            backgroundImage: "url('https://images.unsplash.com/photo-1522030299830-16b8d3d049fe?w=1920&q=80')",
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />

        {/* Animated stars overlay */}
        <div className="absolute inset-0 overflow-hidden">
          {Array.from({ length: 40 }).map((_, i) => (
            <motion.div
              key={i}
              className="absolute rounded-full bg-white"
              style={{
                width: Math.random() * 2 + 1,
                height: Math.random() * 2 + 1,
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 60}%`,
              }}
              animate={{
                opacity: [0.2, 0.8, 0.2],
              }}
              transition={{
                duration: 2 + Math.random() * 3,
                repeat: Infinity,
                delay: Math.random() * 2,
              }}
            />
          ))}
        </div>

        {/* Noise overlay */}
        <div className="pointer-events-none absolute inset-0 opacity-[0.15] mix-blend-overlay"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
          }}
        />

        {/* Gradient overlay */}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/50 via-black/20 to-black/80" />

        {/* Radial glow */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background: "radial-gradient(ellipse at 30% 80%, rgba(99,102,241,0.15) 0%, transparent 60%)",
          }}
        />

        {/* Navbar */}
        <nav className="absolute left-1/2 top-0 z-20 -translate-x-1/2">
          <div className="flex items-center gap-3 rounded-b-2xl bg-black/80 backdrop-blur-xl px-4 py-2.5 sm:gap-6 md:gap-10 md:rounded-b-3xl md:px-8">
            <span className="text-xl mr-2">🌙</span>
            {navItems.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className="text-[10px] transition-colors hover:text-white sm:text-xs md:text-sm"
                style={{ color: "rgba(225, 224, 204, 0.7)" }}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </nav>

        {/* ISRO badge */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.8 }}
          className="absolute top-6 right-6 z-20 flex items-center gap-2"
        >
          <span className="px-3 py-1.5 text-[10px] font-bold tracking-[0.15em] rounded-full border border-white/10 bg-white/5 backdrop-blur-md text-white/70">
            SIH 2026
          </span>
          <span className="px-3 py-1.5 text-[10px] font-bold tracking-[0.15em] rounded-full border border-indigo-500/30 bg-indigo-500/10 backdrop-blur-md text-indigo-300">
            ISRO × AI
          </span>
        </motion.div>

        {/* Hero content */}
        <div className="absolute bottom-0 left-0 right-0 px-4 pb-2 sm:px-6 md:px-10">
          <div className="grid grid-cols-12 items-end gap-4">

            {/* Title */}
            <div className="col-span-12 lg:col-span-7">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.1, duration: 0.5 }}
                className="mb-2 flex items-center gap-2"
              >
                <div className="h-px w-8 bg-indigo-400/60" />
                <span className="text-[11px] font-medium tracking-[0.2em] text-indigo-300/80 uppercase">
                  Chandrayaan-2 Mission
                </span>
              </motion.div>
              <h1
                className="font-bold leading-[0.85] tracking-[-0.06em] text-[15vw] sm:text-[13vw] md:text-[11vw] lg:text-[9vw] xl:text-[8vw]"
                style={{ color: "#E1E0CC" }}
              >
                <WordsPullUp text="Lunar" />
                <br />
                <WordsPullUpMultiStyle
                  segments={[
                    { text: "Feature", className: "bg-gradient-to-r from-indigo-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent" },
                    { text: "Match" },
                  ]}
                />
              </h1>
            </div>

            {/* Right content */}
            <div className="col-span-12 flex flex-col gap-5 pb-6 lg:col-span-5 lg:pb-10">

              <motion.p
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.8, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="text-xs sm:text-sm md:text-base max-w-md"
                style={{ lineHeight: 1.4, color: "rgba(225, 224, 204, 0.65)" }}
              >
                AI-powered multi-modal image correspondence for Chandrayaan-2
                satellite imagery. Finding matching features across OHRC, TMC-2 and
                IIRS instruments under varying illumination and scale conditions.
              </motion.p>

              {/* Stats row */}
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.8, delay: 0.6, ease: [0.16, 1, 0.3, 1] }}
                className="flex gap-6"
              >
                {statsItems.map((stat) => (
                  <div key={stat.label} className="flex flex-col items-center gap-1">
                    <stat.icon className="h-4 w-4 text-indigo-400/70" />
                    <span className="text-sm font-bold text-white/90 font-mono">{stat.value}</span>
                    <span className="text-[9px] text-white/40 uppercase tracking-wider">{stat.label}</span>
                  </div>
                ))}
              </motion.div>

              {/* CTA buttons */}
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.8, delay: 0.7, ease: [0.16, 1, 0.3, 1] }}
                className="flex items-center gap-3"
              >
                <Link
                  href="/demo"
                  className="group inline-flex items-center gap-2 rounded-full bg-indigo-500 py-1.5 pl-5 pr-1.5 text-sm font-semibold text-white transition-all hover:bg-indigo-400 hover:gap-3"
                >
                  Live Demo
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-black/30 transition-transform group-hover:scale-110">
                    <ArrowRight className="h-4 w-4 text-white" />
                  </span>
                </Link>
                <Link
                  href="#pipeline"
                  className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 backdrop-blur-md px-5 py-2.5 text-sm font-medium text-white/70 transition-all hover:border-white/30 hover:text-white/90"
                >
                  View Pipeline
                </Link>
              </motion.div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export { ChandrayaanHero };
