# AI Screen Activity Analyzer (v2.0.0)

A production-grade Python desktop application designed to continuously record user screen activity, detect meaningful interactions, and leverage Google Gemini AI to generate automated, intelligent workflow documentation.

## ✨ Key Features

- **Live & Video Processing**: Record your screen live, or upload existing video files for automated processing.
- **Event-Driven Captures**: Instead of blindly taking screenshots every second, the engine captures high-fidelity frames exclusively on explicit user actions (left/right/double clicks) or detected video scene changes, minimizing disk bloat and API costs.
- **Visual UI Annotation**: Automatically crops, highlights, and draws precision crosshairs over the exact UI elements interacted with before sending them to the AI.
- **Multi-Layer AI Filtering**: Uses mathematical SSIM (Structural Similarity) and aggressive Gemini prompt engineering to ignore loading screens, duplicate frames, and low-value transitions.
- **OCR Integration**: Runs `EasyOCR` on frames to extract visible text, giving the AI deeper context into the application state.
- **Intelligent Workflow Summaries**: Uses **Gemini 2.5 Flash** (via Vertex AI Structured Outputs) to convert raw events into cohesive, story-driven timelines and executive summaries.
- **Production Reporting**: Compiles the final AI timeline, metrics, and annotated screenshots into a beautifully formatted, shareable PDF report using `ReportLab`.
- **Modern PyQt5 Dashboard**: A sleek, dark-mode desktop interface featuring live event tracking, real-time statistics, and a fully interactive timeline.
- **Robust Persistence**: Backed by a local `SQLite` database to persist session data, screenshots, and AI timeline states across app restarts.

## 🏗 Architecture

- `src/gui/`: Modern PyQt5 frontend with non-blocking QThread background workers.
- `src/core/screenshot.py`: `mss` high-speed capture engine with OpenCV visual annotations.
- `src/core/video.py`: Headless video processor with frame-differencing scene detection.
- `src/core/tracker.py`: `pynput` and `pywin32` hooks for global mouse and active window tracking.
- `src/core/analyzer.py`: AI communication layer using `google-genai` and strict Pydantic schemas.
- `src/reporting/`: Generates structured markdown timelines and compiles final PDF deliverables.
- `src/db/database.py`: SQLite wrapper for reliable state management.

## 🚀 Setup Instructions

### 1. Prerequisites
- **Python 3.11+**
- **Windows OS** (Relies on `pywin32` for active window tracking)

### 2. Installation
Clone the repository and set up a Python virtual environment:
```bash
python -m venv ai_screen_venv
ai_screen_venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Authentication
The application uses **Google Vertex AI** (`google-genai` SDK). Ensure you have a valid Google Cloud Service Account key.
Save your `service_account.json` file directly into the root directory of the project, or point to it manually:
```bash
set GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service_account.json"
```

### 4. Configuration
Create a `.env` file in the root directory to configure your specific parameters:
```env
PROJECT_ID=your-gcp-project-id
LOCATION=asia-south1
GEMINI_MODEL=gemini-2.5-flash
SCREENSHOT_ON_CLICK=True
```

## 🎮 Usage

From the activated virtual environment, launch the application:
```bash
python src/main.py
```

1. **Dashboard**: Monitor live statistics and real-time application logs.
2. **Start Recording**: Click `▶ Start Recording` to begin monitoring your workflow. The app will quietly track interactions in the background.
3. **Perform Actions**: Click through your target application. The tracker will map your actions and annotate screenshots.
4. **Stop Recording**: Click `■ Stop Recording`. 
5. **Generate AI Report**: Navigate to the **Reports** tab and click `✦ Generate Full AI Report`. The system will run the SSIM filters, process OCR, batch-analyze the frames with Gemini, and build the final PDF.
6. **Video Uploads**: Alternatively, use the `📁 Upload Video` button on the dashboard to analyze pre-recorded sessions and automatically extract key workflow scenes.

All generated assets (Screenshots, Databases, Timeline JSONs, PDFs) are safely stored in the auto-generated `output/` directory!
