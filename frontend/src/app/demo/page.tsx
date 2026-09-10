"use client";

import React, { useState, useEffect, useCallback } from "react";
import styles from "./demo.module.css";
import MatchViewer from "@/components/MatchViewer";
import ConfidenceGauge from "@/components/ConfidenceGauge";
import ProcessingStatus from "@/components/ProcessingStatus";
import { ResultsResponse } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface GalleryImage {
  id: string;
  instrument: string;
  filename: string;
  width: number;
  height: number;
  resolution_m: number;
  sun_elevation: number | null;
  area: string | null;
  acquisition_date: string | null;
  thumbnail_url: string | null;
  lat_range: string | null;
  lon_range: string | null;
}

type DemoState = "select" | "processing" | "results" | "error";

export default function LiveDemo() {
  const [images, setImages] = useState<GalleryImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedA, setSelectedA] = useState<GalleryImage | null>(null);
  const [selectedB, setSelectedB] = useState<GalleryImage | null>(null);
  const [demoState, setDemoState] = useState<DemoState>("select");
  const [progress, setProgress] = useState({ status: "", progress_percent: 0, current_step: "", message: "" });
  const [results, setResults] = useState<ResultsResponse | null>(null);
  const [error, setError] = useState("");

  // Fetch gallery images
  useEffect(() => {
    const fetchImages = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/gallery/images`, {
          headers: { "ngrok-skip-browser-warning": "true" },
        });
        if (res.ok) {
          const data = await res.json();
          setImages(data);
        }
      } catch (e) {
        console.error("Failed to fetch gallery:", e);
      } finally {
        setLoading(false);
      }
    };
    fetchImages();
  }, []);

  const handleRun = useCallback(async () => {
    if (!selectedA || !selectedB) return;

    setDemoState("processing");
    setError("");

    try {
      // Start the pipeline
      const startRes = await fetch(`${API_BASE}/api/gallery/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true",
        },
        body: JSON.stringify({
          image_a_id: selectedA.id,
          image_b_id: selectedB.id,
        }),
      });

      if (!startRes.ok) {
        throw new Error(`Failed to start: ${await startRes.text()}`);
      }

      const { job_id } = await startRes.json();

      // Poll for status
      const poll = async () => {
        const statusRes = await fetch(`${API_BASE}/api/gallery/status/${job_id}`, {
          headers: { "ngrok-skip-browser-warning": "true" },
        });
        const status = await statusRes.json();

        setProgress({
          status: status.status,
          progress_percent: status.progress_percent,
          current_step: status.current_step,
          message: status.message,
        });

        if (status.status === "completed") {
          const resultsRes = await fetch(`${API_BASE}/api/gallery/results/${job_id}`, {
            headers: { "ngrok-skip-browser-warning": "true" },
          });
          const result = await resultsRes.json();
          setResults(result);
          setDemoState("results");
          return;
        }

        if (status.status === "failed") {
          setError(status.error || "Pipeline failed");
          setDemoState("error");
          return;
        }

        setTimeout(poll, 1500);
      };

      setTimeout(poll, 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
      setDemoState("error");
    }
  }, [selectedA, selectedB]);

  const handleReset = useCallback(() => {
    setDemoState("select");
    setSelectedA(null);
    setSelectedB(null);
    setResults(null);
    setError("");
  }, []);

  const ohrcImages = images.filter((img) => img.instrument === "OHRC");
  const tmcImages = images.filter((img) => img.instrument === "TMC");

  return (
    <main className={styles.main}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div className={styles.logo}>
            <span className={styles.logoIcon}>🌙</span>
            <div>
              <h1 className={styles.logoTitle}>Chandrayaan-2</h1>
              <p className={styles.logoSubtitle}>Live Demo — Image Gallery</p>
            </div>
          </div>
          <div className={styles.badges}>
            <a href="/" className={styles.navLink}>← Back to Upload</a>
            <span className={styles.liveBadge}>
              <span className={styles.liveDot} />
              LIVE
            </span>
          </div>
        </div>
      </header>

      {/* Selection */}
      {demoState === "select" && (
        <section className={styles.selectSection}>
          <h2 className={styles.sectionTitle}>
            Select Two Images to <span className={styles.gradient}>Match</span>
          </h2>
          <p className={styles.sectionDesc}>
            Choose any two Chandrayaan-2 images from the gallery below. The pipeline
            will run live on the T4 GPU and display results in real-time.
          </p>

          {loading ? (
            <div className={styles.loadingState}>
              <div className={styles.spinner} />
              <p>Loading image gallery from server...</p>
            </div>
          ) : images.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No images found. Make sure the data is mounted on the server.</p>
            </div>
          ) : (
            <>
              {/* Selection indicators */}
              <div className={styles.selectionBar}>
                <div className={`${styles.selectionSlot} ${selectedA ? styles.filled : ""}`}>
                  {selectedA ? (
                    <>
                      <span className={styles.slotInstrument}>{selectedA.instrument}</span>
                      <span className={styles.slotName}>{selectedA.filename.slice(0, 25)}...</span>
                      <button className={styles.clearBtn} onClick={() => setSelectedA(null)}>✕</button>
                    </>
                  ) : (
                    <span className={styles.slotPlaceholder}>Select Image A</span>
                  )}
                </div>
                <span className={styles.vsText}>↔</span>
                <div className={`${styles.selectionSlot} ${selectedB ? styles.filled : ""}`}>
                  {selectedB ? (
                    <>
                      <span className={styles.slotInstrument}>{selectedB.instrument}</span>
                      <span className={styles.slotName}>{selectedB.filename.slice(0, 25)}...</span>
                      <button className={styles.clearBtn} onClick={() => setSelectedB(null)}>✕</button>
                    </>
                  ) : (
                    <span className={styles.slotPlaceholder}>Select Image B</span>
                  )}
                </div>
                <button
                  className={`${styles.runBtn} ${!(selectedA && selectedB) ? styles.disabled : ""}`}
                  onClick={handleRun}
                  disabled={!(selectedA && selectedB)}
                >
                  🚀 Run Pipeline Live
                </button>
              </div>

              {/* OHRC Gallery */}
              {ohrcImages.length > 0 && (
                <div className={styles.gallerySection}>
                  <h3 className={styles.galleryTitle}>🔭 OHRC — Orbiter High Resolution Camera (0.25 m/px)</h3>
                  <div className={styles.galleryGrid}>
                    {ohrcImages.map((img) => (
                      <div
                        key={img.id}
                        className={`${styles.imageCard} ${
                          selectedA?.id === img.id || selectedB?.id === img.id ? styles.selected : ""
                        }`}
                        onClick={() => {
                          if (selectedA?.id === img.id) { setSelectedA(null); return; }
                          if (selectedB?.id === img.id) { setSelectedB(null); return; }
                          if (!selectedA) setSelectedA(img);
                          else if (!selectedB) setSelectedB(img);
                        }}
                      >
                        <div className={styles.cardThumb}>
                          {img.thumbnail_url && (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={`${API_BASE}${img.thumbnail_url}`}
                              alt={img.filename}
                              className={styles.thumbImg}
                              crossOrigin="anonymous"
                            />
                          )}
                          {(selectedA?.id === img.id || selectedB?.id === img.id) && (
                            <div className={styles.selectedOverlay}>
                              {selectedA?.id === img.id ? "A" : "B"}
                            </div>
                          )}
                        </div>
                        <div className={styles.cardInfo}>
                          <div className={styles.cardName}>{img.filename.slice(8, 35)}</div>
                          <div className={styles.cardMeta}>
                            <span>{img.width.toLocaleString()}×{img.height.toLocaleString()}</span>
                            <span>{img.resolution_m} m/px</span>
                          </div>
                          {img.sun_elevation && (
                            <div className={styles.cardMeta}>
                              <span>☀️ {img.sun_elevation.toFixed(1)}°</span>
                              <span>{img.area || ""}</span>
                            </div>
                          )}
                          {img.lat_range && (
                            <div className={styles.cardCoords}>📍 {img.lat_range}</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TMC Gallery */}
              {tmcImages.length > 0 && (
                <div className={styles.gallerySection}>
                  <h3 className={styles.galleryTitle}>📷 TMC-2 — Terrain Mapping Camera (5 m/px)</h3>
                  <div className={styles.galleryGrid}>
                    {tmcImages.map((img) => (
                      <div
                        key={img.id}
                        className={`${styles.imageCard} ${
                          selectedA?.id === img.id || selectedB?.id === img.id ? styles.selected : ""
                        }`}
                        onClick={() => {
                          if (selectedA?.id === img.id) { setSelectedA(null); return; }
                          if (selectedB?.id === img.id) { setSelectedB(null); return; }
                          if (!selectedA) setSelectedA(img);
                          else if (!selectedB) setSelectedB(img);
                        }}
                      >
                        <div className={styles.cardThumb}>
                          {img.thumbnail_url && (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={`${API_BASE}${img.thumbnail_url}`}
                              alt={img.filename}
                              className={styles.thumbImg}
                              crossOrigin="anonymous"
                            />
                          )}
                          {(selectedA?.id === img.id || selectedB?.id === img.id) && (
                            <div className={styles.selectedOverlay}>
                              {selectedA?.id === img.id ? "A" : "B"}
                            </div>
                          )}
                        </div>
                        <div className={styles.cardInfo}>
                          <div className={styles.cardName}>{img.filename.slice(8, 35)}</div>
                          <div className={styles.cardMeta}>
                            <span>{img.width.toLocaleString()}×{img.height.toLocaleString()}</span>
                            <span>{img.resolution_m} m/px</span>
                          </div>
                          {img.sun_elevation && (
                            <div className={styles.cardMeta}>
                              <span>☀️ {img.sun_elevation.toFixed(1)}°</span>
                              <span>{img.area || ""}</span>
                            </div>
                          )}
                          {img.lat_range && (
                            <div className={styles.cardCoords}>📍 {img.lat_range}</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </section>
      )}

      {/* Processing */}
      {demoState === "processing" && (
        <section className={styles.processingSection}>
          <ProcessingStatus
            status={progress.status}
            progress={progress.progress_percent}
            currentStep={progress.current_step}
            message={progress.message}
          />
          <p className={styles.processingHint}>
            Running on Tesla T4 GPU • Real Chandrayaan-2 data
          </p>
        </section>
      )}

      {/* Results */}
      {demoState === "results" && results && (
        <section className={styles.resultsSection}>
          <div className={styles.resultsHeader}>
            <h2 className={styles.sectionTitle}>
              <span className={styles.gradient}>Live Results</span>
            </h2>
            <button className={styles.resetBtn} onClick={handleReset}>← Choose New Pair</button>
          </div>

          <div className={styles.topRow}>
            <div className={styles.gaugeCard}>
              <ConfidenceGauge score={results.confidence_score} />
              <div className={styles.gaugeMeta}>
                <div className={styles.metaItem}>
                  <span className={styles.metaValue}>{results.total_matches}</span>
                  <span className={styles.metaLabel}>Verified</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaValue}>{results.processing_time_seconds}s</span>
                  <span className={styles.metaLabel}>Time</span>
                </div>
              </div>
            </div>

            <div className={styles.infoCards}>
              <div className={styles.infoCard}>
                <div className={styles.infoIcon}>🔬</div>
                <div className={styles.infoValue}>{typeof results.stats.raw_matches === "number" ? results.stats.raw_matches : "—"}</div>
                <div className={styles.infoLabel}>Raw Matches</div>
              </div>
              <div className={styles.infoCard}>
                <div className={styles.infoIcon}>✅</div>
                <div className={styles.infoValue}>{results.total_matches}</div>
                <div className={styles.infoLabel}>MAGSAC++ Verified</div>
              </div>
              <div className={styles.infoCard}>
                <div className={styles.infoIcon}>📏</div>
                <div className={styles.infoValue}>
                  {typeof results.stats.avg_reprojection_error === "number"
                    ? `${(results.stats.avg_reprojection_error as number).toFixed(2)}px`
                    : "—"}
                </div>
                <div className={styles.infoLabel}>Reproj. Error</div>
              </div>
            </div>
          </div>

          <MatchViewer
            matches={results.matches}
            imageAWidth={results.image_a.width}
            imageAHeight={results.image_a.height}
            imageBWidth={results.image_b.width}
            imageBHeight={results.image_b.height}
            instrumentA={results.image_a.instrument}
            instrumentB={results.image_b.instrument}
          />

          <div className={styles.tableContainer}>
            <h3 className={styles.tableTitle}>Match Coordinates</h3>
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
                  {results.matches.slice(0, 20).map((m) => (
                    <tr key={m.match_id}>
                      <td>{m.match_id + 1}</td>
                      <td>({m.image_a_pixel.x.toFixed(0)}, {m.image_a_pixel.y.toFixed(0)})</td>
                      <td>({m.image_b_pixel.x.toFixed(0)}, {m.image_b_pixel.y.toFixed(0)})</td>
                      <td>{m.lunar_a.lat.toFixed(4)}, {m.lunar_a.lon.toFixed(4)}</td>
                      <td>{m.lunar_b.lat.toFixed(4)}, {m.lunar_b.lon.toFixed(4)}</td>
                      <td>
                        <div className={styles.confBar}>
                          <div className={styles.confFill} style={{
                            width: `${m.confidence * 100}%`,
                            background: m.confidence > 0.85 ? "#50dc8c" : m.confidence > 0.7 ? "#fbbf24" : "#f87171"
                          }} />
                          <span>{(m.confidence * 100).toFixed(0)}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {/* Error */}
      {demoState === "error" && (
        <section className={styles.errorSection}>
          <div className={styles.errorCard}>
            <span>⚠️</span>
            <h3>Pipeline Error</h3>
            <p>{error}</p>
            <button className={styles.resetBtn} onClick={handleReset}>← Try Again</button>
          </div>
        </section>
      )}

      <footer className={styles.footer}>
        <p>Chandrayaan-2 Image Correspondence System • SIH 2026 • LoFTR + MAGSAC++ on Tesla T4</p>
      </footer>
    </main>
  );
}
