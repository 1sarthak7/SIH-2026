"use client";

import React, { useRef, useEffect, useState } from "react";
import styles from "./MatchViewer.module.css";

interface Match {
  match_id: number;
  image_a_pixel: { x: number; y: number };
  image_b_pixel: { x: number; y: number };
  confidence: number;
}

interface MatchViewerProps {
  matches: Match[];
  imageAWidth: number;
  imageAHeight: number;
  imageBWidth: number;
  imageBHeight: number;
  instrumentA: string;
  instrumentB: string;
}

function getConfidenceColor(conf: number): string {
  if (conf > 0.85) return "#50dc8c";
  if (conf > 0.75) return "#fbbf24";
  return "#f87171";
}

export default function MatchViewer({
  matches,
  imageAWidth,
  imageAHeight,
  imageBWidth,
  imageBHeight,
  instrumentA,
  instrumentB,
}: MatchViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredMatch, setHoveredMatch] = useState<number | null>(null);
  const [showLines, setShowLines] = useState(true);
  const [showPoints, setShowPoints] = useState(true);

  const CANVAS_W = 1200;
  const GAP = 60;
  const HALF_W = (CANVAS_W - GAP) / 2;

  const scaleA = Math.min(HALF_W / imageAWidth, 400 / imageAHeight);
  const scaleB = Math.min(HALF_W / imageBWidth, 400 / imageBHeight);

  const imgA_w = imageAWidth * scaleA;
  const imgA_h = imageAHeight * scaleA;
  const imgB_w = imageBWidth * scaleB;
  const imgB_h = imageBHeight * scaleB;

  const CANVAS_H = Math.max(imgA_h, imgB_h) + 80;

  const imgA_x = (HALF_W - imgA_w) / 2;
  const imgA_y = (CANVAS_H - imgA_h) / 2;
  const imgB_x = HALF_W + GAP + (HALF_W - imgB_w) / 2;
  const imgB_y = (CANVAS_H - imgB_h) / 2;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = CANVAS_W * dpr;
    canvas.height = CANVAS_H * dpr;
    canvas.style.width = `${CANVAS_W}px`;
    canvas.style.height = `${CANVAS_H}px`;
    ctx.scale(dpr, dpr);

    // Background
    ctx.fillStyle = "#0a0e17";
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

    // Image A placeholder
    const gradA = ctx.createLinearGradient(imgA_x, imgA_y, imgA_x + imgA_w, imgA_y + imgA_h);
    gradA.addColorStop(0, "#1a1f2e");
    gradA.addColorStop(1, "#12161f");
    ctx.fillStyle = gradA;
    ctx.fillRect(imgA_x, imgA_y, imgA_w, imgA_h);
    ctx.strokeStyle = "#2a3040";
    ctx.lineWidth = 1;
    ctx.strokeRect(imgA_x, imgA_y, imgA_w, imgA_h);

    // Simulated lunar terrain texture for A
    ctx.globalAlpha = 0.3;
    for (let i = 0; i < 200; i++) {
      const cx = imgA_x + Math.random() * imgA_w;
      const cy = imgA_y + Math.random() * imgA_h;
      const r = 1 + Math.random() * 8;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fillStyle = `hsl(220, 10%, ${15 + Math.random() * 20}%)`;
      ctx.fill();
    }
    ctx.globalAlpha = 1;

    // Image B placeholder
    const gradB = ctx.createLinearGradient(imgB_x, imgB_y, imgB_x + imgB_w, imgB_y + imgB_h);
    gradB.addColorStop(0, "#12161f");
    gradB.addColorStop(1, "#1a1f2e");
    ctx.fillStyle = gradB;
    ctx.fillRect(imgB_x, imgB_y, imgB_w, imgB_h);
    ctx.strokeStyle = "#2a3040";
    ctx.strokeRect(imgB_x, imgB_y, imgB_w, imgB_h);

    ctx.globalAlpha = 0.3;
    for (let i = 0; i < 200; i++) {
      const cx = imgB_x + Math.random() * imgB_w;
      const cy = imgB_y + Math.random() * imgB_h;
      const r = 1 + Math.random() * 8;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fillStyle = `hsl(220, 10%, ${15 + Math.random() * 20}%)`;
      ctx.fill();
    }
    ctx.globalAlpha = 1;

    // Labels
    ctx.font = "bold 14px 'Inter', sans-serif";
    ctx.textAlign = "center";
    ctx.fillStyle = "#7b8baa";
    ctx.fillText(`Image A — ${instrumentA.toUpperCase()}`, imgA_x + imgA_w / 2, imgA_y - 12);
    ctx.fillText(`Image B — ${instrumentB.toUpperCase()}`, imgB_x + imgB_w / 2, imgB_y - 12);

    // Draw match lines
    if (showLines) {
      matches.forEach((m, i) => {
        const ax = imgA_x + (m.image_a_pixel.x / imageAWidth) * imgA_w;
        const ay = imgA_y + (m.image_a_pixel.y / imageAHeight) * imgA_h;
        const bx = imgB_x + (m.image_b_pixel.x / imageBWidth) * imgB_w;
        const by = imgB_y + (m.image_b_pixel.y / imageBHeight) * imgB_h;

        const isHovered = hoveredMatch === i;
        const alpha = isHovered ? 1.0 : 0.4;
        const lineWidth = isHovered ? 2.5 : 1;
        const color = getConfidenceColor(m.confidence);

        ctx.beginPath();
        ctx.moveTo(ax, ay);

        // Curved bezier line
        const midX = (ax + bx) / 2;
        const midY = Math.min(ay, by) - 20;
        ctx.quadraticCurveTo(midX, midY, bx, by);

        ctx.strokeStyle = color;
        ctx.globalAlpha = alpha;
        ctx.lineWidth = lineWidth;
        ctx.stroke();
        ctx.globalAlpha = 1;
      });
    }

    // Draw keypoints
    if (showPoints) {
      matches.forEach((m, i) => {
        const ax = imgA_x + (m.image_a_pixel.x / imageAWidth) * imgA_w;
        const ay = imgA_y + (m.image_a_pixel.y / imageAHeight) * imgA_h;
        const bx = imgB_x + (m.image_b_pixel.x / imageBWidth) * imgB_w;
        const by = imgB_y + (m.image_b_pixel.y / imageBHeight) * imgB_h;

        const isHovered = hoveredMatch === i;
        const radius = isHovered ? 6 : 4;
        const color = getConfidenceColor(m.confidence);

        // Point A
        ctx.beginPath();
        ctx.arc(ax, ay, radius, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        if (isHovered) {
          ctx.strokeStyle = "#fff";
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // Point B
        ctx.beginPath();
        ctx.arc(bx, by, radius, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        if (isHovered) {
          ctx.strokeStyle = "#fff";
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      });
    }

    // Center gap indicator
    ctx.fillStyle = "#1e2432";
    ctx.fillRect(HALF_W, 0, GAP, CANVAS_H);
    ctx.font = "bold 20px 'Inter', sans-serif";
    ctx.textAlign = "center";
    ctx.fillStyle = "#4a5568";
    ctx.fillText("↔", HALF_W + GAP / 2, CANVAS_H / 2);

  }, [matches, hoveredMatch, showLines, showPoints, CANVAS_H,
      imgA_x, imgA_y, imgA_w, imgA_h, imgB_x, imgB_y, imgB_w, imgB_h,
      imageAWidth, imageAHeight, imageBWidth, imageBHeight,
      instrumentA, instrumentB, HALF_W]);

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <button
          className={`${styles.toolBtn} ${showLines ? styles.active : ""}`}
          onClick={() => setShowLines(!showLines)}
        >
          ╌ Lines
        </button>
        <button
          className={`${styles.toolBtn} ${showPoints ? styles.active : ""}`}
          onClick={() => setShowPoints(!showPoints)}
        >
          ● Points
        </button>
        <span className={styles.matchCount}>{matches.length} correspondences</span>
      </div>
      <div className={styles.canvasWrapper}>
        <canvas
          ref={canvasRef}
          className={styles.canvas}
          onMouseMove={(e) => {
            const rect = (e.target as HTMLCanvasElement).getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;

            let closest = -1;
            let minDist = 20;
            matches.forEach((m, i) => {
              const ax = imgA_x + (m.image_a_pixel.x / imageAWidth) * imgA_w;
              const ay = imgA_y + (m.image_a_pixel.y / imageAHeight) * imgA_h;
              const d = Math.sqrt((mx - ax) ** 2 + (my - ay) ** 2);
              if (d < minDist) { minDist = d; closest = i; }

              const bx = imgB_x + (m.image_b_pixel.x / imageBWidth) * imgB_w;
              const by = imgB_y + (m.image_b_pixel.y / imageBHeight) * imgB_h;
              const d2 = Math.sqrt((mx - bx) ** 2 + (my - by) ** 2);
              if (d2 < minDist) { minDist = d2; closest = i; }
            });
            setHoveredMatch(closest >= 0 ? closest : null);
          }}
          onMouseLeave={() => setHoveredMatch(null)}
        />
      </div>
      <div className={styles.legend}>
        <span className={styles.legendItem}>
          <span className={styles.dot} style={{ background: "#50dc8c" }} /> &gt;85%
        </span>
        <span className={styles.legendItem}>
          <span className={styles.dot} style={{ background: "#fbbf24" }} /> 75-85%
        </span>
        <span className={styles.legendItem}>
          <span className={styles.dot} style={{ background: "#f87171" }} /> &lt;75%
        </span>
      </div>
    </div>
  );
}
