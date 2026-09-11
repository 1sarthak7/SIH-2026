"use client";

import React, { useState, useCallback, useRef } from "react";
import { motion, useInView } from "framer-motion";
import styles from "./page.module.css";
import MatchViewer from "@/components/MatchViewer";
import ConfidenceGauge from "@/components/ConfidenceGauge";
import { ChandrayaanHero } from "@/components/ui/chandrayaan-hero";
import FileUpload, { DropZone, FileError, FileList, FileInfo } from "@/components/ui/file-upload";
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
  const isInView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export default function Home() {
  const [appState, setAppState] = useState<AppState>("upload");
  const [uploadFiles, setUploadFiles] = useState<FileInfo[]>([]);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [results, setResults] = useState<ResultsResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [jobId, setJobId] = useState<string>("");
  const [processingProgress, setProcessingProgress] = useState(0);

  const canSubmit = uploadFiles.length >= 2;

  const handleSubmit = useCallback(async () => {
    if (uploadFiles.length < 2) return;

    const fileA = uploadFiles[0].file;
    const fileB = uploadFiles[1].file;

    setAppState("processing");
    setProcessingProgress(0);
    setError("");

    try {
      const uploadResponse = await uploadImages(fileA, fileB);
      setJobId(uploadResponse.job_id);

      const result = await pollUntilComplete(
        uploadResponse.job_id,
        (status) => {
          setJobStatus(status);
          setProcessingProgress(status.progress_percent);
        }
      );

      setResults(result);
      setAppState("results");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      setAppState("error");
    }
  }, [uploadFiles]);

  const handleDemo = useCallback(() => {
    setResults(DEMO_RESULTS);
    setAppState("results");
  }, []);

  const handleReset = useCallback(() => {
    setAppState("upload");
    setUploadFiles([]);
    setJobStatus(null);
    setResults(null);
    setError("");
    setJobId("");
    setProcessingProgress(0);
  }, []);

  const handleFileSelectChange = (files: FileInfo[]) => {
    setUploadFiles(files);
  };

  const handleRemoveFile = (fileId: string) => {
    setUploadFiles(uploadFiles.filter(f => f.id !== fileId));
  };

  return (
    <main className={styles.main}>
      {/* ── Hero ── */}
      {appState === "upload" && <ChandrayaanHero />}

      {/* ── Upload ── */}
      {appState === "upload" && (
        <section className={styles.uploadWrapper}>
          <Reveal>
            <div className={styles.uploadHeading}>
              <h2 className={styles.uploadTitle}>Upload Satellite Images</h2>
              <p className={styles.uploadSubtitle}>
                Select two Chandrayaan-2 images from different instruments to
                find matching surface features.
              </p>
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <div className={styles.uploadCard}>
              <FileUpload
                files={uploadFiles}
                onFileSelectChange={handleFileSelectChange}
                multiple={true}
                accept=".img,.tif,.tiff,.png,.jpg,.jpeg"
                maxSize={500}
                maxCount={2}
                disabled={false}
              >
                <div className={styles.uploadInner}>
                  <DropZone
                    prompt="Drop two images here, or click to browse"
                    className={styles.dropzone}
                  />
                  <FileError />
                  <FileList
                    onClear={() => setUploadFiles([])}
                    onRemove={handleRemoveFile}
                    canResume={false}
                  />
                </div>
              </FileUpload>
            </div>
          </Reveal>

          <Reveal delay={0.2}>
            <div className={styles.actionRow}>
              <button
                className={`${styles.submitBtn} ${!canSubmit ? styles.disabled : ""}`}
                onClick={handleSubmit}
                disabled={!canSubmit}
              >
                <span>Find Correspondences</span>
                <span className={styles.btnArrow}>→</span>
              </button>

              <button className={styles.demoBtn} onClick={handleDemo}>
                <span>View Demo Results</span>
              </button>
            </div>
          </Reveal>

          {/* Pipeline steps */}
          <Reveal delay={0.3}>
            <div className={styles.pipelineRow}>
              {["Ingest", "Preprocess", "LoFTR Match", "Verify", "Map"].map(
                (step, i) => (
                  <React.Fragment key={step}>
                    {i > 0 && <span className={styles.pipelineSep} />}
                    <span className={styles.pipelineChip}>{step}</span>
                  </React.Fragment>
                )
              )}
            </div>
          </Reveal>
        </section>
      )}

      {/* ── Processing ── */}
      {appState === "processing" && (
        <section className={styles.processingWrapper}>
          <div className={styles.processingInner}>
            <ProgressiveFluxLoader
              value={processingProgress}
              phases={PIPELINE_PHASES}
              textClassName={styles.loaderLabel}
              barClassName={styles.loaderBar}
            />
            <p className={styles.processingMeta}>
              Tesla T4 GPU  /  Real Chandrayaan-2 data
            </p>
          </div>
        </section>
      )}

      {/* ── Results ── */}
      {appState === "results" && results && (
        <section className={styles.resultsSection}>
          <div className={styles.resultsHeader}>
            <h2 className={styles.resultsTitle}>
              <span className={styles.gradient}>Matching Results</span>
            </h2>
            <button className={styles.resetBtn} onClick={handleReset}>
              New Analysis
            </button>
          </div>

          <div className={styles.topStatsRow}>
            <div className={styles.gaugeCard}>
              <ConfidenceGauge score={results.confidence_score} />
              <div className={styles.gaugeMeta}>
                <div className={styles.gaugeMetaItem}>
                  <span className={styles.gaugeMetaValue}>{results.total_matches}</span>
                  <span className={styles.gaugeMetaLabel}>Verified</span>
                </div>
                <div className={styles.gaugeMetaItem}>
                  <span className={styles.gaugeMetaValue}>{results.processing_time_seconds}s</span>
                  <span className={styles.gaugeMetaLabel}>Time</span>
                </div>
              </div>
            </div>

            <div className={styles.statsCards}>
              {[
                { label: "Raw LoFTR Matches", value: typeof results.stats.raw_matches === "number" ? results.stats.raw_matches : "---" },
                { label: "After MNN Filter", value: typeof results.stats.after_mnn === "number" ? results.stats.after_mnn : "---" },
                { label: "MAGSAC++ Verified", value: results.total_matches },
                { label: "Avg Reproj. Error", value: typeof results.stats.avg_reprojection_error === "number" ? `${(results.stats.avg_reprojection_error as number).toFixed(2)} px` : "---" },
                { label: "Sun Elevation A/B", value: typeof results.stats.sun_elevation_a === "number" ? `${(results.stats.sun_elevation_a as number).toFixed(1)} / ${(results.stats.sun_elevation_b as number).toFixed(1)}` : `${results.image_a.instrument.toUpperCase()} / ${results.image_b.instrument.toUpperCase()}` },
                { label: "Latitude Range", value: `${results.image_a.bbox.lat_min.toFixed(2)} to ${results.image_a.bbox.lat_max.toFixed(2)}` },
              ].map((stat) => (
                <div key={stat.label} className={styles.miniStatCard}>
                  <div className={styles.miniStatValue}>{stat.value}</div>
                  <div className={styles.miniStatLabel}>{stat.label}</div>
                </div>
              ))}
            </div>
          </div>

          <div className={styles.viewerSection}>
            <h3 className={styles.sectionTitle}>Feature Correspondence Map</h3>
            <MatchViewer
              matches={results.matches}
              imageAWidth={results.image_a.width}
              imageAHeight={results.image_a.height}
              imageBWidth={results.image_b.width}
              imageBHeight={results.image_b.height}
              instrumentA={results.image_a.instrument}
              instrumentB={results.image_b.instrument}
            />
          </div>

          <div className={styles.imageInfoGrid}>
            <div className={styles.imageInfoCard}>
              <h3 className={styles.imageInfoTitle}>Image A  --  {results.image_a.instrument.toUpperCase()}</h3>
              <div className={styles.imageInfoMeta}>
                <span>{results.image_a.filename}</span>
                <span>{results.image_a.width.toLocaleString()} x {results.image_a.height.toLocaleString()} px</span>
                <span>{results.image_a.resolution_m} m/px</span>
              </div>
            </div>
            <div className={styles.imageInfoCard}>
              <h3 className={styles.imageInfoTitle}>Image B  --  {results.image_b.instrument.toUpperCase()}</h3>
              <div className={styles.imageInfoMeta}>
                <span>{results.image_b.filename}</span>
                <span>{results.image_b.width.toLocaleString()} x {results.image_b.height.toLocaleString()} px</span>
                <span>{results.image_b.resolution_m} m/px</span>
              </div>
            </div>
          </div>

          {results.matches.length > 0 && (
            <div className={styles.tableContainer}>
              <h3 className={styles.tableTitle}>Match Coordinates</h3>
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
                    {results.matches.slice(0, 50).map((m) => (
                      <tr key={m.match_id}>
                        <td className={styles.mono}>{m.match_id + 1}</td>
                        <td className={styles.mono}>
                          ({m.image_a_pixel.x.toFixed(1)}, {m.image_a_pixel.y.toFixed(1)})
                        </td>
                        <td className={styles.mono}>
                          ({m.image_b_pixel.x.toFixed(1)}, {m.image_b_pixel.y.toFixed(1)})
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
                                background:
                                  m.confidence > 0.9 ? "#50dc8c"
                                  : m.confidence > 0.7 ? "#fbbf24"
                                  : "#f87171",
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
              {results.matches.length > 50 && (
                <div className={styles.tableMore}>
                  Showing 50 of {results.matches.length} matches
                </div>
              )}
            </div>
          )}

          <div className={styles.statsDetail}>
            <h3 className={styles.tableTitle}>Pipeline Statistics</h3>
            <div className={styles.statsDetailGrid}>
              {Object.entries(results.stats).map(([key, value]) => (
                <div key={key} className={styles.statsDetailItem}>
                  <span className={styles.statsDetailKey}>{key.replace(/_/g, " ")}</span>
                  <span className={styles.statsDetailValue}>
                    {typeof value === "number" ? value.toFixed(4) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── Error ── */}
      {appState === "error" && (
        <section className={styles.errorSection}>
          <div className={styles.errorCard}>
            <h3 className={styles.errorTitle}>Processing Failed</h3>
            <p className={styles.errorMessage}>{error}</p>
            <button className={styles.resetBtn} onClick={handleReset}>
              Try Again
            </button>
          </div>
        </section>
      )}

      {/* ── Footer ── */}
      <footer className={styles.footer}>
        <p>Built for Smart India Hackathon 2026  /  Powered by LoFTR + Kornia + PyTorch</p>
      </footer>
    </main>
  );
}
