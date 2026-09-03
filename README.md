# 🌙 Chandrayaan-2 Multi-Modal Image Correspondence System

**SIH 2026 — Multi-modal, Sun Angle and Scale Invariant Image Correspondence**

An AI-powered system that finds feature correspondences between Chandrayaan-2 images from different instruments (OHRC, TMC-2, IIRS), handling differences in resolution, illumination, and spectral modality.

## 🏗️ Architecture

```
┌──────────────────┐     ┌────────────────────┐     ┌─────────────┐
│  Next.js Frontend │────▶│  FastAPI Backend    │────▶│  Redis      │
│  (CesiumJS Globe) │◀────│  (PyTorch + LoFTR)  │◀────│  (Queue)    │
└──────────────────┘     └────────────────────┘     └─────────────┘
                                   │
                              ┌────▼────┐
                              │ T4 GPU  │
                              └─────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- CUDA-capable GPU (T4 or better recommended)

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Docker (Full Stack)
```bash
docker-compose up --build
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload two Chandrayaan-2 images |
| `GET` | `/api/jobs/{id}` | Poll processing status |
| `GET` | `/api/results/{id}` | Get matching results |
| `GET` | `/health` | System health check |

## 🔬 Pipeline Steps

1. **Data Ingestion** — Parse PDS4/GeoTIFF via GDAL/Rasterio
2. **Preprocessing** — OHRC(CLAHE) / TMC(Contrast) / IIRS(PCA)
3. **Feature Extraction** — Multi-scale FPN encoder
4. **Cross-Modal Matching** — LoFTR Transformer
5. **Outlier Rejection** — MNN + MAGSAC++
6. **Geospatial Mapping** — Pixel → Lunar lat/lon
7. **3D Visualization** — CesiumJS Moon globe

## 🛠️ Tech Stack

- **Frontend:** Next.js 14, TypeScript, CesiumJS (via Resium)
- **Backend:** FastAPI, Python 3.11
- **ML:** PyTorch 2.x, Kornia (LoFTR), OpenCV
- **Geospatial:** GDAL, Rasterio, PyProj
- **Infrastructure:** Docker, Redis

## 📂 Project Structure

```
SIH-2026/
├── backend/          # FastAPI + ML pipeline
│   ├── app/
│   │   ├── api/      # REST endpoints
│   │   ├── core/     # Configuration
│   │   ├── models/   # Pydantic schemas
│   │   └── services/ # Processing pipeline
│   └── Dockerfile
├── frontend/         # Next.js application
├── ml/               # Training scripts
├── data/             # Sample images (gitignored)
└── docker-compose.yml
```

## 📊 Supported Instruments

| Instrument | Resolution | Bands | Format |
|-----------|-----------|-------|--------|
| OHRC | 0.25 m/px | 1 (Pan) | PDS4 (.img) |
| TMC-2 | 5 m/px | 1-3 (Stereo) | GeoTIFF |
| IIRS | 80 m/px | 256 (Hyperspectral) | PDS4 (.img) |

## 📜 License

Built for Smart India Hackathon 2026.
