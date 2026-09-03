/**
 * API client for communicating with the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UploadResponse {
  job_id: string;
  status: string;
  message: string;
  created_at: string;
}

export interface JobStatus {
  job_id: string;
  status: string;
  progress_percent: number;
  current_step: string;
  message: string;
  created_at?: string;
  completed_at?: string;
  error?: string;
}

export interface MatchResult {
  match_id: number;
  image_a_pixel: { x: number; y: number };
  image_b_pixel: { x: number; y: number };
  lunar_a: { lat: number; lon: number };
  lunar_b: { lat: number; lon: number };
  confidence: number;
}

export interface ImageInfo {
  instrument: string;
  filename: string;
  width: number;
  height: number;
  resolution_m: number;
  bbox: {
    lat_min: number;
    lat_max: number;
    lon_min: number;
    lon_max: number;
  };
}

export interface ResultsResponse {
  job_id: string;
  status: string;
  image_a: ImageInfo;
  image_b: ImageInfo;
  matches: MatchResult[];
  total_matches: number;
  confidence_score: number;
  processing_time_seconds: number;
  stats: Record<string, number | string>;
}

/**
 * Upload two images for processing
 */
export async function uploadImages(
  imageA: File,
  imageB: File
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("image_a", imageA);
  formData.append("image_b", imageB);

  const response = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Upload failed");
  }

  return response.json();
}

/**
 * Poll job status
 */
export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to get job status");
  }

  return response.json();
}

/**
 * Get results for a completed job
 */
export async function getResults(jobId: string): Promise<ResultsResponse> {
  const response = await fetch(`${API_BASE}/api/results/${jobId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to get results");
  }

  return response.json();
}

/**
 * Get processed image URL for display
 */
export function getImageUrl(jobId: string, which: "a" | "b"): string {
  return `${API_BASE}/api/results/${jobId}/image/${which}`;
}

/**
 * Poll job status until completion
 */
export async function pollUntilComplete(
  jobId: string,
  onProgress: (status: JobStatus) => void,
  intervalMs: number = 2000
): Promise<ResultsResponse> {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getJobStatus(jobId);
        onProgress(status);

        if (status.status === "completed") {
          const results = await getResults(jobId);
          resolve(results);
          return;
        }

        if (status.status === "failed") {
          reject(new Error(status.error || "Processing failed"));
          return;
        }

        // Continue polling
        setTimeout(poll, intervalMs);
      } catch (err) {
        reject(err);
      }
    };

    poll();
  });
}
