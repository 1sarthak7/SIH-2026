"use client";

import React, { useCallback, useState } from "react";
import styles from "./UploadDropzone.module.css";

interface UploadDropzoneProps {
  label: string;
  accept?: string;
  onFileSelect: (file: File) => void;
  selectedFile: File | null;
  instrumentHint?: string;
}

export default function UploadDropzone({
  label,
  accept,
  onFileSelect,
  selectedFile,
  instrumentHint,
}: UploadDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) onFileSelect(file);
    },
    [onFileSelect]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFileSelect(file);
    },
    [onFileSelect]
  );

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div
      className={`${styles.dropzone} ${isDragging ? styles.dragging : ""} ${
        selectedFile ? styles.hasFile : ""
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        type="file"
        accept={accept || ".img,.tif,.tiff,.png,.jpg,.jpeg,.fits"}
        onChange={handleInputChange}
        className={styles.fileInput}
        id={`upload-${label}`}
      />
      <label htmlFor={`upload-${label}`} className={styles.label}>
        {selectedFile ? (
          <div className={styles.fileInfo}>
            <div className={styles.fileIcon}>📡</div>
            <div className={styles.fileName}>{selectedFile.name}</div>
            <div className={styles.fileSize}>{formatSize(selectedFile.size)}</div>
            <div className={styles.changeHint}>Click to change</div>
          </div>
        ) : (
          <div className={styles.placeholder}>
            <div className={styles.uploadIcon}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <div className={styles.title}>{label}</div>
            <div className={styles.subtitle}>
              Drag & drop or click to browse
            </div>
            {instrumentHint && (
              <div className={styles.hint}>{instrumentHint}</div>
            )}
            <div className={styles.formats}>
              Supports: .img, .tif, .png, .jpg, .fits
            </div>
          </div>
        )}
      </label>
    </div>
  );
}
