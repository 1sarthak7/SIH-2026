/**
 * Demo data from actual Chandrayaan-2 OHRC pipeline run.
 * 
 * Source: Two OHRC South Pole images
 *  - T0410: Sun elevation 5.54°, lat ~-85.45°
 *  - T0609: Sun elevation 6.73°, lat ~-85.32°
 * 
 * Pipeline: LoFTR → MNN → MAGSAC++ 
 * Result: 1979 raw → 1828 MNN → 39 verified
 */

import { ResultsResponse } from "./api";

// Generate realistic match data based on actual pipeline output
function generateDemoMatches() {
  const matches = [];
  // Real stats: 39 matches, avg conf 0.79, spread across 5 strip sections
  const baseMatches = [
    { ax: 3421, ay: 5123, bx: 3502, by: 4891, conf: 0.851 },
    { ax: 7832, ay: 12045, bx: 7901, by: 11823, conf: 0.823 },
    { ax: 2156, ay: 25678, bx: 2234, by: 25401, conf: 0.817 },
    { ax: 9012, ay: 8934, bx: 9087, by: 8712, conf: 0.831 },
    { ax: 5678, ay: 45123, bx: 5745, by: 44901, conf: 0.806 },
    { ax: 1234, ay: 67890, bx: 1312, by: 67668, conf: 0.793 },
    { ax: 8901, ay: 34567, bx: 8978, by: 34345, conf: 0.828 },
    { ax: 4567, ay: 78901, bx: 4645, by: 78679, conf: 0.787 },
    { ax: 6789, ay: 23456, bx: 6867, by: 23234, conf: 0.804 },
    { ax: 3456, ay: 89012, bx: 3534, by: 88790, conf: 0.769 },
    { ax: 10234, ay: 15678, bx: 10312, by: 15456, conf: 0.812 },
    { ax: 7890, ay: 56789, bx: 7968, by: 56567, conf: 0.795 },
    { ax: 2345, ay: 40123, bx: 2423, by: 39901, conf: 0.776 },
    { ax: 11012, ay: 72345, bx: 11090, by: 72123, conf: 0.808 },
    { ax: 5123, ay: 95012, bx: 5201, by: 94790, conf: 0.782 },
    { ax: 8456, ay: 3456, bx: 8534, by: 3234, conf: 0.836 },
    { ax: 1567, ay: 50123, bx: 1645, by: 49901, conf: 0.754 },
    { ax: 9567, ay: 60789, bx: 9645, by: 60567, conf: 0.798 },
    { ax: 4012, ay: 85678, bx: 4090, by: 85456, conf: 0.771 },
    { ax: 6234, ay: 18901, bx: 6312, by: 18679, conf: 0.821 },
    { ax: 3789, ay: 99012, bx: 3867, by: 98790, conf: 0.756 },
    { ax: 10567, ay: 42345, bx: 10645, by: 42123, conf: 0.789 },
    { ax: 1890, ay: 75678, bx: 1968, by: 75456, conf: 0.802 },
    { ax: 7456, ay: 30123, bx: 7534, by: 29901, conf: 0.765 },
    { ax: 5890, ay: 65012, bx: 5968, by: 64790, conf: 0.818 },
    { ax: 2678, ay: 52345, bx: 2756, by: 52123, conf: 0.791 },
    { ax: 8234, ay: 88901, bx: 8312, by: 88679, conf: 0.777 },
    { ax: 4890, ay: 7890, bx: 4968, by: 7668, conf: 0.843 },
    { ax: 11234, ay: 38012, bx: 11312, by: 37790, conf: 0.786 },
    { ax: 6567, ay: 82345, bx: 6645, by: 82123, conf: 0.753 },
    { ax: 3012, ay: 15012, bx: 3090, by: 14790, conf: 0.808 },
    { ax: 9890, ay: 48567, bx: 9968, by: 48345, conf: 0.794 },
    { ax: 1456, ay: 93012, bx: 1534, by: 92790, conf: 0.762 },
    { ax: 7123, ay: 20678, bx: 7201, by: 20456, conf: 0.826 },
    { ax: 5345, ay: 70123, bx: 5423, by: 69901, conf: 0.779 },
    { ax: 2901, ay: 58901, bx: 2979, by: 58679, conf: 0.801 },
    { ax: 8678, ay: 10234, bx: 8756, by: 10012, conf: 0.835 },
    { ax: 4234, ay: 62345, bx: 4312, by: 62123, conf: 0.758 },
    { ax: 10890, ay: 27890, bx: 10968, by: 27668, conf: 0.813 },
  ];

  for (let i = 0; i < baseMatches.length; i++) {
    const m = baseMatches[i];
    matches.push({
      match_id: i,
      image_a_pixel: { x: m.ax, y: m.ay },
      image_b_pixel: { x: m.bx, y: m.by },
      lunar_a: {
        lat: -85.45 + (m.ay / 101063) * 0.77,
        lon: 23.57 + (m.ax / 12000) * 4.74,
      },
      lunar_b: {
        lat: -85.37 + (m.by / 101074) * 0.82,
        lon: 23.02 + (m.bx / 12000) * 4.71,
      },
      confidence: m.conf,
    });
  }

  return matches;
}

export const DEMO_RESULTS: ResultsResponse = {
  job_id: "demo-ohrc-southpole",
  status: "completed",
  image_a: {
    instrument: "ohrc",
    filename: "ch2_ohr_ncp_20260103T0410224157_d_img_d18.img",
    width: 12000,
    height: 101063,
    resolution_m: 0.25,
    bbox: {
      lat_min: -85.488206,
      lat_max: -84.675992,
      lon_min: 23.571179,
      lon_max: 28.310697,
    },
  },
  image_b: {
    instrument: "ohrc",
    filename: "ch2_ohr_ncp_20260103T0609041371_d_img_d18.img",
    width: 12000,
    height: 101074,
    resolution_m: 0.25,
    bbox: {
      lat_min: -85.365843,
      lat_max: -84.552478,
      lon_min: 23.016352,
      lon_max: 27.723845,
    },
  },
  matches: generateDemoMatches(),
  total_matches: 39,
  confidence_score: 40.7,
  processing_time_seconds: 51.83,
  stats: {
    "raw_matches": 1979,
    "after_mnn": 1828,
    "after_magsac": 39,
    "inlier_ratio": 0.021,
    "avg_reprojection_error": 0.61,
    "max_reprojection_error": 2.34,
    "spatial_spread_avg": 0.18,
    "coordinate_source_a": "geometry_csv",
    "coordinate_source_b": "geometry_csv",
    "sun_elevation_a": 5.537,
    "sun_elevation_b": 6.729,
  },
};
