"use client";

import React from "react";
import styles from "./ProcessingStatus.module.css";

interface ProcessingStatusProps {
  status: string;
  progress: number;
  currentStep: string;
  message: string;
}

const PIPELINE_STEPS = [
  { key: "ingesting", label: "Ingestion", icon: "📥" },
  { key: "preprocessing", label: "Preprocessing", icon: "⚙️" },
  { key: "matching", label: "Feature Matching", icon: "🧠" },
  { key: "verifying", label: "Verification", icon: "✅" },
  { key: "mapping", label: "Geospatial Mapping", icon: "🌍" },
  { key: "completed", label: "Complete", icon: "🎉" },
];

export default function ProcessingStatus({
  status,
  progress,
  currentStep,
  message,
}: ProcessingStatusProps) {
  const currentIndex = PIPELINE_STEPS.findIndex((s) => s.key === status);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Processing Pipeline</h2>
        <div className={styles.percentage}>{Math.round(progress)}%</div>
      </div>

      {/* Progress bar */}
      <div className={styles.progressTrack}>
        <div
          className={styles.progressFill}
          style={{ width: `${progress}%` }}
        />
        <div
          className={styles.progressGlow}
          style={{ left: `${progress}%` }}
        />
      </div>

      {/* Step indicators */}
      <div className={styles.steps}>
        {PIPELINE_STEPS.map((step, index) => {
          let stepState = "pending";
          if (index < currentIndex) stepState = "completed";
          else if (index === currentIndex) stepState = "active";

          return (
            <div
              key={step.key}
              className={`${styles.step} ${styles[stepState]}`}
            >
              <div className={styles.stepDot}>
                {stepState === "completed" ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : stepState === "active" ? (
                  <div className={styles.pulse} />
                ) : (
                  <div className={styles.emptyDot} />
                )}
              </div>
              <div className={styles.stepIcon}>{step.icon}</div>
              <div className={styles.stepLabel}>{step.label}</div>
            </div>
          );
        })}
      </div>

      {/* Current status message */}
      <div className={styles.message}>
        <div className={styles.messageIcon}>
          {status === "completed" ? "✅" : status === "failed" ? "❌" : "⏳"}
        </div>
        <div className={styles.messageText}>{message}</div>
      </div>
    </div>
  );
}
