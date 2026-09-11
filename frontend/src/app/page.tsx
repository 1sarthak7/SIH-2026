"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion, useInView } from "framer-motion";
import styles from "./page.module.css";
import MatchViewer from "@/components/MatchViewer";
import ConfidenceGauge from "@/components/ConfidenceGauge";
import { FishyFileDrop } from "@/components/ui/fishy-file-drop";
import { ProgressiveFluxLoader } from "@/components/ui/progressive-flux-loader";
import { uploadImages, pollUntilComplete, ResultsResponse, JobStatus } from "@/lib/api";
import { DEMO_RESULTS } from "@/lib/demoData";

type AppState = "upload" | "processing" | "results" | "error";

const PIPELINE_PHASES = [
  { at: 0, label: "ingesting" },
  { at: 15, label: "preprocessing" },
  { at: 40, label: "matching features" },
  { at: 70, label: "verifying" },
  { at: 85, label: "mapping coordinates" },
  { at: 100, label: "complete" },
];

/* ── Scroll-reveal wrapper ── */
function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.8, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/* ── Pipeline steps data ── */
const PIPELINE_STEPS = [
  {
    step: "01",
    title: "Ingestion",
    desc: "Parse PDS4 labels, extract spatial metadata, load raw pixel data from OHRC, TMC-2, and IIRS instruments.",
  },
  {
    step: "02",
    title: "Preprocessing",
    desc: "CLAHE contrast enhancement, multi-band PCA reduction, adaptive histogram equalization, and patch extraction.",
  },
  {
    step: "03",
    title: "Feature Matching",
    desc: "LoFTR deep feature matching across all patch pairs. Dense correspondence without explicit keypoint detection.",
  },
  {
    step: "04",
    title: "Verification",
    desc: "Mutual nearest neighbor check followed by MAGSAC++ geometric verification with adaptive thresholds.",
  },
  {
    step: "05",
    title: "Coordinate Mapping",
    desc: "Convert verified pixel matches to lunar lat/lon using per-pixel geometry grids from ISRO PRADAN.",
  },
  {
    step: "06",
    title: "Results",
    desc: "Confidence scoring, spatial spread analysis, reprojection error stats, and exportable match table.",
  },
];

const TECH_STACK = [
  "PyTorch", "LoFTR", "Kornia", "OpenCV", "MAGSAC++",
  "Next.js", "FastAPI", "GDAL", "Rasterio", "Docker",
];

export default function Home() {
  const [appState, setAppState] = useState<AppState>("upload");
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [results, setResults] = useState<ResultsResponse | null>(null);
  const [error, setError] = useState("");
  const [jobId, setJobId] = useState("");
  const [processingProgress, setProcessingProgress] = useState(0);

  const canSubmit = fileA !== null && fileB !== null;

  const handleFileA = useCallback((files: FileList) => {
    if (files[0]) setFileA(files[0]);
  }, []);

  const handleFileB = useCallback((files: FileList) => {
    if (files[0]) setFileB(files[0]);
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return;
    setAppState("processing");
    setProcessingProgress(0);

    try {
      if (!fileA || !fileB) throw new Error("Need both images.");

      const data = await uploadImages(fileA, fileB);
      setJobId(data.job_id);

      const result = await pollUntilComplete(data.job_id, (status) => {
        setJobStatus(status);
        setProcessingProgress(status.progress_percent);
      });

      setResults(result);
      setAppState("results");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Processing failed.");
      setAppState("error");
    }
  }, [canSubmit, uploadFiles]);

  const handleDemo = useCallback(() => {
    setAppState("processing");
    setProcessingProgress(0);

    const steps = [5, 15, 30, 50, 70, 85, 100];
    steps.forEach((p, i) => {
      setTimeout(() => {
        setProcessingProgress(p);
        if (p === 100) {
          setTimeout(() => {
            setResults(DEMO_RESULTS as unknown as ResultsResponse);
            setAppState("results");
          }, 500);
        }
      }, (i + 1) * 700);
    });
  }, []);

  const handleReset = useCallback(() => {
    setAppState("upload");
    setFileA(null);
    setFileB(null);
    setResults(null);
    setError("");
    setJobId("");
    setProcessingProgress(0);
  }, []);

  return (
    <main className={styles.main}>
      {/* ════ Navbar ════ */}
      <nav className={styles.navbar}>
        <div className={styles.navInner}>
          <div className={styles.navLogo}>
            <div>
              <div className={styles.navLogoText}>Chandrayaan-2</div>
              <div className={styles.navLogoSub}>Team Moosambi</div>
            </div>
          </div>
          <ul className={styles.navLinks}>
            <li><a href="#hero" className={styles.navLink}>Home</a></li>
            <li><a href="#pipeline" className={styles.navLink}>Pipeline</a></li>
            <li><a href="#upload" className={styles.navLink}>Live Demo</a></li>
            <li><a href="#about" className={styles.navLink}>About</a></li>
            <li><a href="#contact" className={styles.navLink}>Contact</a></li>
          </ul>
        </div>
      </nav>

      {/* ════ Hero ════ */}
      <section id="hero" className={styles.hero}>
        <div className={styles.heroInner}>
          <Reveal className={styles.heroText}>
            <div className={styles.heroLabel}>ISRO / SIH 2026 / Multi-Modal</div>
            <h1 className={styles.heroTitle}>
              Lunar Feature{" "}
              <span className={styles.heroTitleItalic}>Matching</span>
            </h1>
            <p className={styles.heroDesc}>
              AI-powered image correspondence system for Chandrayaan-2 satellite
              imagery. Finding matching features across OHRC, TMC-2 and IIRS
              instruments under varying sun angles and scale conditions.
            </p>
            <div className={styles.heroActions}>
              <a href="#upload" className={styles.btnPrimary}>
                Try Live Demo
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </a>
              <a href="#pipeline" className={styles.btnSecondary}>
                View Pipeline
              </a>
            </div>
          </Reveal>
          <Reveal className={styles.heroMoon} delay={0.3}>
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 120, repeat: Infinity, ease: "linear" }}
              style={{
                width: "clamp(280px, 28vw, 380px)",
                height: "clamp(280px, 28vw, 380px)",
                borderRadius: "50%",
                overflow: "hidden",
                filter: "drop-shadow(0 16px 48px rgba(0,0,0,0.12))",
              }}
            >
              <Image
                src="/moon.jpg"
                alt="Moon"
                width={400}
                height={400}
                className="rounded-full object-cover"
                priority
              />
            </motion.div>
          </Reveal>
        </div>
      </section>

      {/* ════ Pipeline ════ */}
      <div className={styles.divider}><div className={styles.dividerLine} /></div>
      <section id="pipeline" className={styles.section}>
        <Reveal>
          <div className={styles.sectionLabel}>How It Works</div>
          <h2 className={styles.sectionTitle}>The Processing Pipeline</h2>
          <p className={styles.sectionDesc}>
            Six carefully orchestrated stages transform raw Chandrayaan-2 imagery
            into verified feature correspondences with lunar coordinate mapping.
          </p>
        </Reveal>
        <div className={styles.pipelineGrid}>
          {PIPELINE_STEPS.map((step, i) => (
            <Reveal key={step.step} delay={i * 0.1}>
              <div className={styles.pipelineCard}>
                <div className={styles.pipelineStep}>Step {step.step}</div>
                <div className={styles.pipelineCardTitle}>{step.title}</div>
                <div className={styles.pipelineCardDesc}>{step.desc}</div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ════ Upload / Processing / Results ════ */}
      <div className={styles.divider}><div className={styles.dividerLine} /></div>

      {appState === "upload" && (
        <section id="upload" className={styles.section}>
          <Reveal>
            <div className={styles.sectionLabel}>Live Demo</div>
            <h2 className={styles.sectionTitle}>Upload Your Images</h2>
            <p className={styles.sectionDesc}>
              Upload two Chandrayaan-2 images to find feature correspondences.
              Supports OHRC, TMC-2, and IIRS instruments in IMG, TIF, and FITS formats.
            </p>
          </Reveal>
          <Reveal delay={0.15}>
            <div style={{ display: "flex", gap: 24, justifyContent: "center", flexWrap: "wrap" }}>
              {/* Image A */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                <div style={{
                  display: "flex", justifyContent: "center", alignItems: "center",
                  background: "#161616", borderRadius: 22,
                }}>
                  <FishyFileDrop
                    id="drop-image-a"
                    width="300px"
                    height="300px"
                    padding="14px"
                    backgroundImageWidth="96px"
                    borderWidth="2px"
                    borderColor="#363636"
                    borderRadius="20px"
                    shadow="0 2px 15px rgba(255, 255, 255, 0.1)"
                    innerBorderRadius="10px"
                    fishColor="white"
                    waveColors={["#1b70a1", "#368cc1", "#50a8e0", "#6bc4ff"]}
                    bubbleColor="rgba(255,255,255,0.8)"
                    textColor="#fff"
                    textStroke="#6BC4FF"
                    textSize="20px"
                    letterSpacingHover="8px"
                    text={fileA ? fileA.name.slice(0, 16) : "Image A"}
                    onFilesSelected={handleFileA}
                  />
                </div>
                <span style={{ fontSize: "0.72rem", color: fileA ? "var(--accent-green)" : "var(--text-muted)", fontFamily: "JetBrains Mono, monospace" }}>
                  {fileA ? `${(fileA.size / 1024 / 1024).toFixed(1)} MB` : "OHRC / TMC / IIRS"}
                </span>
              </div>

              {/* Image B */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                <div style={{
                  display: "flex", justifyContent: "center", alignItems: "center",
                  background: "#161616", borderRadius: 22,
                }}>
                  <FishyFileDrop
                    id="drop-image-b"
                    width="300px"
                    height="300px"
                    padding="14px"
                    backgroundImageWidth="96px"
                    borderWidth="2px"
                    borderColor="#363636"
                    borderRadius="20px"
                    shadow="0 2px 15px rgba(255, 255, 255, 0.1)"
                    innerBorderRadius="10px"
                    fishColor="white"
                    waveColors={["#1b70a1", "#368cc1", "#50a8e0", "#6bc4ff"]}
                    bubbleColor="rgba(255,255,255,0.8)"
                    textColor="#fff"
                    textStroke="#6BC4FF"
                    textSize="20px"
                    letterSpacingHover="8px"
                    text={fileB ? fileB.name.slice(0, 16) : "Image B"}
                    onFilesSelected={handleFileB}
                  />
                </div>
                <span style={{ fontSize: "0.72rem", color: fileB ? "var(--accent-green)" : "var(--text-muted)", fontFamily: "JetBrains Mono, monospace" }}>
                  {fileB ? `${(fileB.size / 1024 / 1024).toFixed(1)} MB` : "OHRC / TMC / IIRS"}
                </span>
              </div>
            </div>

            <div className={styles.actionRow} style={{ marginTop: 32 }}>
              <button
                className={styles.btnPrimary}
                onClick={handleSubmit}
                disabled={!canSubmit}
                style={{ opacity: canSubmit ? 1 : 0.4 }}
              >
                Start Processing
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
              <button className={styles.btnSecondary} onClick={handleDemo}>
                Try Demo Data
              </button>
            </div>
          </Reveal>
        </section>
      )}

      {appState === "processing" && (
        <section id="upload" className={styles.section}>
          <div className={styles.processingWrapper}>
            <div className={styles.processingInner}>
              <ProgressiveFluxLoader
                value={processingProgress}
                phases={PIPELINE_PHASES}
                style={{
                  "--flux-from": "#2563EB",
                  "--flux-to": "#06B6D4",
                } as React.CSSProperties}
              />
              <div className={styles.processingMeta}>
                {jobId ? `Job ${jobId.slice(0, 8)}...` : "Processing with demo data..."}
              </div>
            </div>
          </div>
        </section>
      )}

      {appState === "results" && results && (
        <section id="upload" className={styles.resultsSection}>
          <div className={styles.resultsHeader}>
            <h2 className={styles.resultsTitle}>
              {results.total_matches} Correspondences Found
            </h2>
            <button className={styles.resetBtn} onClick={handleReset}>
              New Analysis
            </button>
          </div>

          {/* Stats Row */}
          <div className={styles.topStatsRow}>
            <div className={styles.gaugeCard}>
              <ConfidenceGauge value={results.confidence_score} size={140} />
              <div className={styles.gaugeMeta}>
                <div className={styles.gaugeMetaItem}>
                  <span className={styles.gaugeMetaValue}>{results.total_matches}</span>
                  <span className={styles.gaugeMetaLabel}>Matches</span>
                </div>
                <div className={styles.gaugeMetaItem}>
                  <span className={styles.gaugeMetaValue}>{results.processing_time_seconds}s</span>
                  <span className={styles.gaugeMetaLabel}>Time</span>
                </div>
              </div>
            </div>
            <div className={styles.statsCards}>
              {Object.entries(results.stats || {}).slice(0, 6).map(([key, val]) => (
                <div key={key} className={styles.miniStatCard}>
                  <div className={styles.miniStatValue}>
                    {typeof val === "number" ? (val % 1 === 0 ? val : val.toFixed(2)) : String(val)}
                  </div>
                  <div className={styles.miniStatLabel}>
                    {key.replace(/_/g, " ")}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Image Info */}
          <div className={styles.imageInfoGrid}>
            {[results.image_a, results.image_b].map((img, idx) => (
              <div key={idx} className={styles.imageInfoCard}>
                <div className={styles.imageInfoTitle}>
                  Image {idx === 0 ? "A" : "B"}: {img.instrument.toUpperCase()}
                </div>
                <div className={styles.imageInfoMeta}>
                  <span>{img.filename}</span>
                  <span>{img.width}x{img.height}</span>
                  <span>{img.resolution_m} m/px</span>
                </div>
              </div>
            ))}
          </div>

          {/* Match Viewer */}
          <div className={styles.viewerSection}>
            <MatchViewer results={results} />
          </div>

          {/* Match Table */}
          <div className={styles.tableContainer}>
            <div className={styles.tableTitle}>Top Correspondences</div>
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Image A (px)</th>
                    <th>Image B (px)</th>
                    <th>Lunar A</th>
                    <th>Lunar B</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {results.matches.slice(0, 15).map((m) => (
                    <tr key={m.match_id}>
                      <td className={styles.mono}>{m.match_id + 1}</td>
                      <td className={styles.mono}>
                        {m.image_a_pixel.x.toFixed(1)}, {m.image_a_pixel.y.toFixed(1)}
                      </td>
                      <td className={styles.mono}>
                        {m.image_b_pixel.x.toFixed(1)}, {m.image_b_pixel.y.toFixed(1)}
                      </td>
                      <td className={styles.mono}>
                        {m.lunar_a.lat.toFixed(4)}, {m.lunar_a.lon.toFixed(4)}
                      </td>
                      <td className={styles.mono}>
                        {m.lunar_b.lat.toFixed(4)}, {m.lunar_b.lon.toFixed(4)}
                      </td>
                      <td>
                        <div className={styles.confidenceBar}>
                          <div
                            className={styles.confidenceFill}
                            style={{
                              width: `${m.confidence * 100}%`,
                              maxWidth: 80,
                              background: m.confidence > 0.85
                                ? "var(--accent-green)"
                                : m.confidence > 0.7
                                  ? "var(--accent-amber)"
                                  : "var(--accent-red)",
                            }}
                          />
                          <span>{(m.confidence * 100).toFixed(0)}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Additional Stats */}
          {Object.keys(results.stats || {}).length > 6 && (
            <div className={styles.statsDetail}>
              <div className={styles.tableTitle}>Pipeline Statistics</div>
              <div className={styles.statsDetailGrid}>
                {Object.entries(results.stats).map(([key, val]) => (
                  <div key={key} className={styles.statsDetailItem}>
                    <span className={styles.statsDetailKey}>
                      {key.replace(/_/g, " ")}
                    </span>
                    <span className={styles.statsDetailValue}>
                      {typeof val === "number"
                        ? val % 1 === 0 ? val : val.toFixed(4)
                        : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {appState === "error" && (
        <section className={styles.section}>
          <div className={styles.errorSection}>
            <div className={styles.errorCard}>
              <div className={styles.errorTitle}>Processing Failed</div>
              <div className={styles.errorMessage}>{error}</div>
              <button className={styles.btnPrimary} onClick={handleReset}>
                Try Again
              </button>
            </div>
          </div>
        </section>
      )}

      {/* ════ About ════ */}
      <div className={styles.divider}><div className={styles.dividerLine} /></div>
      <section id="about" className={styles.section}>
        <Reveal>
          <div className={styles.sectionLabel}>About the Project</div>
          <h2 className={styles.sectionTitle}>Built by Team Moosambi</h2>
        </Reveal>
        <div className={styles.aboutGrid}>
          <Reveal delay={0.1}>
            <div className={styles.aboutText}>
              <p style={{ marginBottom: 16 }}>
                This system addresses the challenge of finding correspondences between
                multi-modal images captured by Chandrayaan-2 instruments -- OHRC
                (0.25m resolution), TMC-2 (5m), and IIRS (hyperspectral) -- where
                traditional feature matching fails due to extreme scale differences,
                varying sun angles, and different spectral responses.
              </p>
              <p>
                Our approach uses LoFTR-based dense feature matching with a custom
                preprocessing pipeline designed for ISRO PDS4 data formats.
                MAGSAC++ verification ensures geometric consistency, while per-pixel
                geometry grids from PRADAN enable accurate lunar coordinate mapping.
              </p>
            </div>
          </Reveal>
          <Reveal delay={0.2}>
            <div className={styles.aboutCard}>
              <div className={styles.aboutCardTitle}>Technology Stack</div>
              <ul className={styles.techList}>
                {TECH_STACK.map((tech) => (
                  <li key={tech} className={styles.techChip}>{tech}</li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ════ Contact ════ */}
      <div className={styles.divider}><div className={styles.dividerLine} /></div>
      <section id="contact" className={styles.section}>
        <Reveal>
          <div className={styles.sectionLabel}>Get in Touch</div>
          <h2 className={styles.sectionTitle}>Contact Us</h2>
          <p className={styles.sectionDesc}>
            Interested in our work or want to collaborate? Reach out to Team Moosambi.
          </p>
        </Reveal>
        <Reveal delay={0.1}>
          <div className={styles.contactGrid}>
            <div className={styles.contactCard}>
              <div className={styles.contactLabel}>Email</div>
              <div className={styles.contactValue}>moosambi@example.com</div>
            </div>
            <div className={styles.contactCard}>
              <div className={styles.contactLabel}>GitHub</div>
              <div className={styles.contactValue}>github.com/1sarthak7/SIH-2026</div>
            </div>
            <div className={styles.contactCard}>
              <div className={styles.contactLabel}>Location</div>
              <div className={styles.contactValue}>India</div>
            </div>
          </div>
        </Reveal>
      </section>

      {/* ════ Footer ════ */}
      <footer className={styles.footer}>
        Team Moosambi / Smart India Hackathon 2026 / ISRO Chandrayaan-2
      </footer>
    </main>
  );
}
