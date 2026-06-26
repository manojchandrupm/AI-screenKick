import traceback
from pathlib import Path
# pyrefly: ignore [missing-import]
import cv2
# pyrefly: ignore [missing-import]
from skimage.metrics import structural_similarity as ssim
# pyrefly: ignore [missing-import]
from PyQt5.QtCore import QThread, pyqtSignal

from src.db.database import DatabaseManager
from src.core.analyzer import AIAnalyzer
from src.reporting.exporter import ReportExporter
from src.reporting.timeline import build_timeline
from src.config import config
from src.core.video import VideoProcessor

class AnalysisWorker(QThread):
    """Runs AI analysis + report generation in background."""
    progress  = pyqtSignal(int, str)
    finished  = pyqtSignal(dict)
    error     = pyqtSignal(str)

    def __init__(self, session_id: int, parent=None):
        super().__init__(parent)
        self.session_id = session_id

    def run(self):
        try:
            db = DatabaseManager(config.OUTPUT_DIR / "ai_screen_processor.db")
            analyzer = AIAnalyzer()
            exporter = ReportExporter()

            self.progress.emit(5, "Loading session data…")
            session     = db.get_session(self.session_id)
            events      = db.get_events(self.session_id)
            screenshots = db.get_screenshots(self.session_id)

            self.progress.emit(15, "Building timeline…")
            timeline = build_timeline(events, screenshots)

            # Analyze screenshots that haven't been analyzed yet
            unanalyzed = [
                s for s in screenshots
                if not s.get("ai_description") and s.get("filepath")
                and Path(s["filepath"]).exists()
            ]
            
            total = len(unanalyzed)
            
            # Find the last unique frame to compare against
            last_unique_gray = None
            for s in reversed(screenshots):
                desc = s.get("ai_description", "")
                if desc and "IGNORE_SCREENSHOT" not in desc and Path(s["filepath"]).exists():
                    try:
                        img = cv2.imread(s["filepath"])
                        if img is not None:
                            last_unique_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                            break
                    except Exception:
                        pass

            # 1. Filter with SSIM and Extract OCR
            ocr_map = {}
            filtered_unanalyzed = []
            
            for i, ss in enumerate(unanalyzed):
                self.progress.emit(
                    15 + int(30 * i / max(total, 1)),
                    f"Filtering & Extracting text {i+1}/{total}…"
                )
                
                is_duplicate = False
                try:
                    img = cv2.imread(ss["filepath"])
                    if img is not None:
                        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        if last_unique_gray is not None:
                            # Compare shapes first just in case
                            if gray.shape == last_unique_gray.shape:
                                score, _ = ssim(last_unique_gray, gray, full=True)
                                if score > 0.90:
                                    is_duplicate = True
                        
                        if not is_duplicate:
                            last_unique_gray = gray
                except Exception:
                    pass
                
                if is_duplicate:
                    db.update_screenshot_analysis(
                        ss["id"],
                        ocr_text="",
                        ai_description="IGNORE_SCREENSHOT"
                    )
                else:
                    extracted_text = analyzer.extract_text(ss["filepath"])
                    ocr_map[ss["id"]] = extracted_text
                    
                    from src.core.privacy import PrivacyFilter
                    if PrivacyFilter.is_blacklisted(extracted_text):
                        db.update_screenshot_analysis(
                            ss["id"],
                            ocr_text=extracted_text,
                            ai_description="IGNORE_SCREENSHOT"
                        )
                    else:
                        filtered_unanalyzed.append(ss)

            # 2. Batch AI Analysis for filtered screenshots
            if filtered_unanalyzed:
                self.progress.emit(45, f"AI Batch Analyzing {len(filtered_unanalyzed)} unique frames...")
                
                # Use the newly improved batch analyzer
                batch_results = analyzer.analyze_session_batch(filtered_unanalyzed, ocr_map=ocr_map)
                
                self.progress.emit(75, "Saving batch analysis results...")
                
                # Update the database with the results
                for result in batch_results:
                    ss_id = result["id"]
                    ai_desc = result.get("ai_description", "IGNORE_SCREENSHOT")
                    
                    db.update_screenshot_analysis(
                        ss_id,
                        ocr_text=ocr_map.get(ss_id, ""),
                        ai_description=ai_desc,
                        ui_elements=result.get("ui_elements", "")
                    )

            # Refresh with analysis
            screenshots = db.get_screenshots(self.session_id)
            timeline    = build_timeline(events, screenshots)

            self.progress.emit(80, "AI Workflow Context & Filtering…")
            filtered_timeline, summary = analyzer.filter_and_summarize_workflow(timeline)
            db.update_session_summary(self.session_id, summary)

            self.progress.emit(90, "Exporting reports…")
            session = db.get_session(self.session_id)
            paths   = exporter.export_all(session, filtered_timeline, summary)

            self.progress.emit(100, "Done!")
            self.finished.emit(paths)

        except Exception as e:
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")

class VideoUploadWorker(QThread):
    """Processes uploaded video to extract keyframes."""
    progress  = pyqtSignal(int, str)
    new_screenshot = pyqtSignal(dict)
    finished  = pyqtSignal()
    error     = pyqtSignal(str)

    def __init__(self, session_id: int, video_path: str, db, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.video_path = video_path
        self.db = db

    def run(self):
        try:
            processor = VideoProcessor(self.video_path)
            for phase, current_frame, total_frames, raw_path, elapsed_seconds, event_type in processor.process():
                pct = int((current_frame / max(1, total_frames)) * 100)
                if phase == "analyzing":
                    self.progress.emit(pct, f"Analyzing Video Flow... {pct}%")
                else:
                    self.progress.emit(pct, f"Extracting Keyframes... {pct}%")
                
                if raw_path:
                    # Provide the specific event_type (click or scene_change) to the DB
                    trigger = f"video_{event_type}" if event_type != "none" else "video_frame"
                    ss_id = self.db.insert_screenshot(self.session_id, raw_path, trigger)
                    self.new_screenshot.emit({
                        "id": ss_id,
                        "filepath": raw_path,
                        "annotated_path": "",
                        "trigger_type": trigger,
                        "timestamp": f"{elapsed_seconds:.2f}s"
                    })
            self.progress.emit(100, "Extraction complete!")
            self.finished.emit()
        except Exception as e:
            self.error.emit(f"Video Processing Error: {e}\\n{traceback.format_exc()}")
