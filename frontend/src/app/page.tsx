"use client";

import React, { useState, useCallback } from "react";
import styles from "./page.module.css";
import UploadDropzone from "@/components/UploadDropzone";
import ProcessingStatus from "@/components/ProcessingStatus";
import MatchViewer from "@/components/MatchViewer";
import ConfidenceGauge from "@/components/ConfidenceGauge";
import { uploadImages, pollUntilComplete, ResultsResponse, JobStatus } from "@/lib/api";
import { DEMO_RESULTS } from "@/lib/demoData";

type AppState = "upload" | "processing" | "results" | "error";

export default function Home() {
  const [appState, setAppState] = useState<AppState>("upload");
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [results, setResults] = useState<ResultsResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [jobId, setJobId] = useState<string>("");

  const canSubmit = fileA !== null && fileB !== null;

  const handleSubmit = useCallback(async () => {
    if (!fileA || !fileB) return;

    setAppState("processing");
    setError("");

    try {
      const uploadResponse = await uploadImages(fileA, fileB);
      setJobId(uploadResponse.job_id);

      const result = await pollUntilComplete(
        uploadResponse.job_id,
        (status) => setJobStatus(status)
      );

      setResults(result);
      setAppState("results");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      setAppState("error");
    }
  }, [fileA, fileB]);

  const handleDemo = useCallback(() => {
    setResults(DEMO_RESULTS);
    setAppState("results");
  }, []);

  const handleReset = useCallback(() => {
    setAppState("upload");
    setFileA(null);
    setFileB(null);
    setJobStatus(null);
    setResults(null);
    setError("");
    setJobId("");
  }, []);

  return (
    <main className={styles.main}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div className={styles.logo}>
            <span className={styles.logoIcon}>🌙</span>
            <div>
              <h1 className={styles.logoTitle}>Chandrayaan-2</h1>
              <p className={styles.logoSubtitle}>Image Correspondence System</p>
            </div>
          </div>
          <div className={styles.badges}>
            <span className={styles.badge}>SIH 2026</span>
            <span className={styles.badge}>ISRO</span>
            <span className={styles.badgeAccent}>AI-Powered</span>
          </div>
        </div>
      </header>

      {/* Hero */}
      {appState === "upload" && (
        <section className={styles.hero}>
          <div className={styles.heroGlow} />
          <h2 className={styles.heroTitle}>
            Multi-Modal Feature{" "}
            <span className={styles.gradient}>Correspondence</span>
          </h2>
          <p className={styles.heroDesc}>
            Upload two Chandrayaan-2 images from different instruments to find
            matching features across modalities, scales, and illumination conditions.
          </p>

          {/* Instrument Cards */}
          <div className={styles.instruments}>
            <div className={styles.instrumentCard}>
              <div className={styles.instrumentIcon}>🔭</div>
              <div className={styles.instrumentName}>OHRC</div>
              <div className={styles.instrumentRes}>0.25 m/px</div>
            </div>
            <div className={styles.instrumentCard}>
              <div className={styles.instrumentIcon}>📷</div>
              <div className={styles.instrumentName}>TMC-2</div>
              <div className={styles.instrumentRes}>5 m/px</div>
            </div>
            <div className={styles.instrumentCard}>
              <div className={styles.instrumentIcon}>🌈</div>
              <div className={styles.instrumentName}>IIRS</div>
              <div className={styles.instrumentRes}>80 m/px · 256 bands</div>
            </div>
          </div>
        </section>
      )}

      {/* Upload Section */}
      {appState === "upload" && (
        <section className={styles.uploadSection}>
          <div className={styles.uploadGrid}>
            <UploadDropzone
              label="Image A"
              onFileSelect={setFileA}
              selectedFile={fileA}
              instrumentHint="e.g., OHRC high-resolution image"
            />
            <div className={styles.vsIndicator}>
              <div className={styles.vsLine} />
              <span className={styles.vsText}>↔</span>
              <div className={styles.vsLine} />
            </div>
            <UploadDropzone
              label="Image B"
              onFileSelect={setFileB}
              selectedFile={fileB}
              instrumentHint="e.g., TMC or IIRS image"
            />
          </div>

          <div className={styles.buttonRow}>
            <button
              className={`${styles.submitBtn} ${!canSubmit ? styles.disabled : ""}`}
              onClick={handleSubmit}
              disabled={!canSubmit}
            >
              <span className={styles.btnIcon}>🚀</span>
              <span>Find Correspondences</span>
              <span className={styles.btnArrow}>→</span>
            </button>

            <button className={styles.demoBtn} onClick={handleDemo}>
              <span>▶</span>
              <span>View Demo Results</span>
            </button>
          </div>

          {/* Pipeline preview */}
          <div className={styles.pipelinePreview}>
            <div className={styles.pipelineStep}>📥 Ingest</div>
            <div className={styles.pipelineArrow}>→</div>
            <div className={styles.pipelineStep}>⚙️ Preprocess</div>
            <div className={styles.pipelineArrow}>→</div>
            <div className={styles.pipelineStep}>🧠 LoFTR Match</div>
            <div className={styles.pipelineArrow}>→</div>
            <div className={styles.pipelineStep}>✅ Verify</div>
            <div className={styles.pipelineArrow}>→</div>
            <div className={styles.pipelineStep}>🌍 Map</div>
          </div>
        </section>
      )}

      {/* Processing Section */}
      {appState === "processing" && jobStatus && (
        <section className={styles.processingSection}>
          <ProcessingStatus
            status={jobStatus.status}
            progress={jobStatus.progress_percent}
            currentStep={jobStatus.current_step}
            message={jobStatus.message}
          />
        </section>
      )}

      {/* Results Section */}
      {appState === "results" && results && (
        <section className={styles.resultsSection}>
          <div className={styles.resultsHeader}>
            <h2 className={styles.resultsTitle}>
              <span className={styles.gradient}>Matching Results</span>
            </h2>
            <button className={styles.resetBtn} onClick={handleReset}>
              ← New Analysis
            </button>
          </div>

          {/* Top Stats Row: Gauge + Cards */}
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
              <div className={styles.miniStatCard}>
                <div className={styles.miniStatIcon}>🔬</div>
                <div>
                  <div className={styles.miniStatValue}>
                    {typeof results.stats.raw_matches === "number" ? results.stats.raw_matches : "—"}
                  </div>
                  <div className={styles.miniStatLabel}>Raw LoFTR Matches</div>
                </div>
              </div>
              <div className={styles.miniStatCard}>
                <div className={styles.miniStatIcon}>🧹</div>
                <div>
                  <div className={styles.miniStatValue}>
                    {typeof results.stats.after_mnn === "number" ? results.stats.after_mnn : "—"}
                  </div>
                  <div className={styles.miniStatLabel}>After MNN Filter</div>
                </div>
              </div>
              <div className={styles.miniStatCard}>
                <div className={styles.miniStatIcon}>✅</div>
                <div>
                  <div className={styles.miniStatValue}>{results.total_matches}</div>
                  <div className={styles.miniStatLabel}>MAGSAC++ Verified</div>
                </div>
              </div>
              <div className={styles.miniStatCard}>
                <div className={styles.miniStatIcon}>📏</div>
                <div>
                  <div className={styles.miniStatValue}>
                    {typeof results.stats.avg_reprojection_error === "number"
                      ? `${(results.stats.avg_reprojection_error as number).toFixed(2)} px`
                      : "—"}
                  </div>
                  <div className={styles.miniStatLabel}>Avg Reprojection Error</div>
                </div>
              </div>
              <div className={styles.miniStatCard}>
                <div className={styles.miniStatIcon}>☀️</div>
                <div>
                  <div className={styles.miniStatValue}>
                    {typeof results.stats.sun_elevation_a === "number"
                      ? `${(results.stats.sun_elevation_a as number).toFixed(1)}° / ${(results.stats.sun_elevation_b as number).toFixed(1)}°`
                      : `${results.image_a.instrument.toUpperCase()} ↔ ${results.image_b.instrument.toUpperCase()}`}
                  </div>
                  <div className={styles.miniStatLabel}>Sun Elevation (A / B)</div>
                </div>
              </div>
              <div className={styles.miniStatCard}>
                <div className={styles.miniStatIcon}>🗺️</div>
                <div>
                  <div className={styles.miniStatValue}>
                    {results.image_a.bbox.lat_min.toFixed(2)}° to {results.image_a.bbox.lat_max.toFixed(2)}°
                  </div>
                  <div className={styles.miniStatLabel}>Latitude Range (South Pole)</div>
                </div>
              </div>
            </div>
          </div>

          {/* Match Viewer */}
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

          {/* Image Info */}
          <div className={styles.imageInfoGrid}>
            <div className={styles.imageInfoCard}>
              <h3 className={styles.imageInfoTitle}>Image A — {results.image_a.instrument.toUpperCase()}</h3>
              <div className={styles.imageInfoMeta}>
                <span>{results.image_a.filename}</span>
                <span>{results.image_a.width.toLocaleString()}×{results.image_a.height.toLocaleString()} px</span>
                <span>{results.image_a.resolution_m} m/px</span>
              </div>
            </div>
            <div className={styles.imageInfoCard}>
              <h3 className={styles.imageInfoTitle}>Image B — {results.image_b.instrument.toUpperCase()}</h3>
              <div className={styles.imageInfoMeta}>
                <span>{results.image_b.filename}</span>
                <span>{results.image_b.width.toLocaleString()}×{results.image_b.height.toLocaleString()} px</span>
                <span>{results.image_b.resolution_m} m/px</span>
              </div>
            </div>
          </div>

          {/* Match Table */}
          {results.matches.length > 0 && (
            <div className={styles.tableContainer}>
              <h3 className={styles.tableTitle}>Feature Correspondences</h3>
              <div className={styles.tableWrapper}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Image A (px)</th>
                      <th>Image B (px)</th>
                      <th>Lunar A (°)</th>
                      <th>Lunar B (°)</th>
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
                                background: m.confidence > 0.9
                                  ? "#50dc8c"
                                  : m.confidence > 0.7
                                  ? "#fbbf24"
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

          {/* Pipeline Statistics */}
          <div className={styles.statsDetail}>
            <h3 className={styles.tableTitle}>Pipeline Statistics</h3>
            <div className={styles.statsDetailGrid}>
              {Object.entries(results.stats).map(([key, value]) => (
                <div key={key} className={styles.statsDetailItem}>
                  <span className={styles.statsDetailKey}>
                    {key.replace(/_/g, " ")}
                  </span>
                  <span className={styles.statsDetailValue}>
                    {typeof value === "number" ? value.toFixed(4) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Error State */}
      {appState === "error" && (
        <section className={styles.errorSection}>
          <div className={styles.errorCard}>
            <div className={styles.errorIcon}>⚠️</div>
            <h3 className={styles.errorTitle}>Processing Failed</h3>
            <p className={styles.errorMessage}>{error}</p>
            <button className={styles.resetBtn} onClick={handleReset}>
              ← Try Again
            </button>
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className={styles.footer}>
        <p>Built for Smart India Hackathon 2026 • Powered by LoFTR + Kornia + PyTorch</p>
      </footer>
    </main>
  );
}
