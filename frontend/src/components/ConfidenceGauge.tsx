"use client";

import React, { useEffect, useState } from "react";
import styles from "./ConfidenceGauge.module.css";

interface ConfidenceGaugeProps {
  score: number; // 0-100
  label?: string;
}

export default function ConfidenceGauge({ score, label = "Confidence" }: ConfidenceGaugeProps) {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const duration = 1500;
    const start = performance.now();
    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(eased * score);
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [score]);

  const radius = 80;
  const stroke = 10;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - (animatedScore / 100) * circumference;

  const getColor = (s: number) => {
    if (s >= 70) return "#50dc8c";
    if (s >= 40) return "#fbbf24";
    return "#f87171";
  };

  const color = getColor(animatedScore);
  const glowColor = getColor(animatedScore) + "40";

  return (
    <div className={styles.gauge}>
      <svg
        width={200}
        height={200}
        viewBox={`0 0 ${(radius + stroke) * 2} ${(radius + stroke) * 2}`}
        className={styles.svg}
      >
        {/* Background track */}
        <circle
          cx={radius + stroke}
          cy={radius + stroke}
          r={radius}
          fill="none"
          stroke="#1e2432"
          strokeWidth={stroke}
        />
        {/* Animated fill */}
        <circle
          cx={radius + stroke}
          cy={radius + stroke}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${radius + stroke} ${radius + stroke})`}
          style={{
            filter: `drop-shadow(0 0 8px ${glowColor})`,
            transition: "stroke 0.3s",
          }}
        />
        {/* Center text */}
        <text
          x={radius + stroke}
          y={radius + stroke - 8}
          textAnchor="middle"
          className={styles.scoreText}
          fill={color}
        >
          {Math.round(animatedScore)}%
        </text>
        <text
          x={radius + stroke}
          y={radius + stroke + 16}
          textAnchor="middle"
          className={styles.labelText}
          fill="#7b8baa"
        >
          {label}
        </text>
      </svg>
    </div>
  );
}
