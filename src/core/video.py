# pyrefly: ignore [missing-import]
import cv2
import time
import logging
from typing import Generator, Tuple, Optional, List
import numpy as np
# pyrefly: ignore [missing-import]
from skimage.metrics import structural_similarity as ssim

from src.core.screenshot import ScreenshotManager

logger = logging.getLogger(__name__)

class VideoProcessor:
    """
    Two-pass video processor.
    
    Pass 1: Scans the entire video to identify meaningful screen transitions using SSIM.
    Pass 2: Seeks back to each transition and saves clean screenshots, deduplicating them.
    """

    def __init__(self, video_path: str, fps_sample_rate: float = 2.0):
        self.video_path = video_path
        self.fps_sample_rate = fps_sample_rate
        self._manager = ScreenshotManager()

        # Tuning parameters
        self.ssim_threshold = 0.85       # Below this = meaningful screen change
        self.debounce_seconds = 3.0      # Minimum gap between transitions

    def _read_frame_at(self, cap: cv2.VideoCapture, frame_idx: int) -> Optional[np.ndarray]:
        """Seek to a specific frame index and read it."""
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_idx - 1))
        ret, frame = cap.read()
        return frame if ret else None

    def process(self) -> Generator[Tuple[str, int, int, Optional[str], float, str], None, None]:
        """
        Main entry point. Runs both passes and yields results.
        Yields: (phase, progress_current, progress_total, saved_path_or_None, elapsed_seconds, event_type)
        """
        # === Pass 1 ===
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            logger.error(f"Pass 1: Failed to open video: {self.video_path}")
            return

        source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_skip = max(1, int(source_fps / self.fps_sample_rate))
        debounce_frames = int(self.debounce_seconds * self.fps_sample_rate)

        logger.info(
            "Pass 1 — Scanning video: source_fps=%.1f, sample_fps=%.1f, "
            "frame_skip=%d, total_frames=%d",
            source_fps, self.fps_sample_rate, frame_skip, total_frames,
        )

        transitions: List[dict] = []
        prev_gray: Optional[np.ndarray] = None
        prev_frame_idx = 0
        frames_since_last_transition = debounce_frames  # Allow first frame
        current_frame = 0
        is_first = True

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            current_frame += 1

            if current_frame % frame_skip != 0:
                if current_frame % int(source_fps) == 0:
                    yield "analyzing", current_frame, total_frames, None, current_frame / source_fps, "none"
                continue

            frame = self._manager.apply_roi(frame)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Downscale for faster SSIM computation
            small = cv2.resize(gray, (480, 270))

            frames_since_last_transition += 1

            if prev_gray is None:
                prev_gray = small
                prev_frame_idx = current_frame
                yield "analyzing", current_frame, total_frames, None, current_frame / source_fps, "none"
                continue

            # Compute SSIM
            score, _ = ssim(prev_gray, small, full=True)

            if is_first and score >= self.ssim_threshold:
                # Capture the very first stable frame as a transition
                transitions.append({
                    "frame_before": 0,
                    "frame_after": current_frame,
                    "elapsed": current_frame / source_fps,
                    "ssim": 1.0,
                })
                is_first = False
                frames_since_last_transition = 0

            if score < self.ssim_threshold and frames_since_last_transition >= debounce_frames:
                transitions.append({
                    "frame_before": prev_frame_idx,
                    "frame_after": current_frame,
                    "elapsed": current_frame / source_fps,
                    "ssim": round(score, 4),
                })
                frames_since_last_transition = 0
                is_first = False

            prev_gray = small
            prev_frame_idx = current_frame
            yield "analyzing", current_frame, total_frames, None, current_frame / source_fps, "none"

        cap.release()
        logger.info(f"Pass 1 complete — {len(transitions)} transitions detected.")

        if not transitions:
            logger.warning("No transitions found in video.")
            return

        # === Pass 2 ===
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            logger.error(f"Pass 2: Failed to open video: {self.video_path}")
            return

        total = len(transitions)
        logger.info(f"Pass 2 — Capturing {total} transition pairs.")

        # Deduplicate: use SSIM on the "after" frames to skip near-identical transitions
        last_saved_gray: Optional[np.ndarray] = None

        for i, t in enumerate(transitions):
            elapsed = t["elapsed"]

            # Read the "after" frame (the new screen state)
            after_frame = self._read_frame_at(cap, t["frame_after"])
            if after_frame is None:
                yield "extracting", i + 1, total, None, elapsed, "scene_change"
                continue

            after_frame = self._manager.apply_roi(after_frame)

            # Deduplicate against the last saved frame
            after_gray = cv2.cvtColor(after_frame, cv2.COLOR_BGR2GRAY)
            after_small = cv2.resize(after_gray, (480, 270))

            if last_saved_gray is not None:
                dup_score, _ = ssim(last_saved_gray, after_small, full=True)
                if dup_score > 0.95:
                    logger.debug(f"Transition {i}: skipped (duplicate, ssim={dup_score:.3f})")
                    yield "extracting", i + 1, total, None, elapsed, "scene_change"
                    continue

            # Save the "after" frame (the meaningful new screen)
            try:
                raw_path, _ = self._manager.save_screenshot(after_frame, f"transition_{i}_")
                last_saved_gray = after_small
                logger.info(f"Transition {i}: saved at {elapsed:.2f}s (ssim={t['ssim']})")
                yield "extracting", i + 1, total, raw_path, elapsed, "scene_change"
            except Exception as e:
                logger.exception(f"Failed to save transition {i}: {e}")
                yield "extracting", i + 1, total, None, elapsed, "scene_change"

        cap.release()
        logger.info("Pass 2 complete.")