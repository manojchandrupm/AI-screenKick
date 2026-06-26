import logging
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field

class SummaryBlock(BaseModel):
    type: str = Field(description="One of: 'h1', 'h2', 'h3', 'paragraph', 'list_item'")
    text: str = Field(description="The text content of the block")

class RetainedScreenshot(BaseModel):
    id: int = Field(description="The integer ID of the screenshot")
    description: str = Field(description="The new rewritten story-driven description")

class SessionReportSchema(BaseModel):
    summary_blocks: List[SummaryBlock]
    retained_screenshots: List[RetainedScreenshot]

class BatchResult(BaseModel):
    id: int
    description: str

class BatchResponseSchema(BaseModel):
    results: List[BatchResult]
    new_summary: str
from google import genai
import ollama
# pyrefly: ignore [missing-import]
from PIL import Image
from src.config import config

try:
    # pyrefly: ignore [missing-import]
    import easyocr
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """Manages text extraction via OCR and semantic analysis via Vertex AI."""

    def __init__(self):
        self.project_id = config.GCP_PROJECT_ID
        self.location = config.GCP_LOCATION
        self.model_name = config.GEMINI_MODEL
        
        self.vision_model = config.OLLAMA_VISION_MODEL
        self.text_model = config.OLLAMA_TEXT_MODEL
        
        # Initialize OCR
        self.ocr_reader = None
        if OCR_AVAILABLE:
            try:
                self.ocr_reader = easyocr.Reader(config.OCR_LANGUAGES, gpu=config.OCR_USE_GPU)
                logger.info("EasyOCR initialized successfully.")
            except Exception as e:
                logger.error(f"EasyOCR failed to initialize: {e}")
                
        # Initialize Vertex AI Client (Gemini)
        try:
            self.client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location
            )
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI client: {e}")
            self.client = None

        # Check Ollama connection
        try:
            ollama.list()
        except Exception as e:
            logger.error(f"Failed to connect to Ollama server. Is it running? {e}")

    def extract_text(self, image_path: str) -> str:
        """Extracts visible text using local OCR."""
        if self.ocr_reader is None:
            return ""
        try:
            results = self.ocr_reader.readtext(image_path)
            return " ".join([res[1] for res in results])
        except Exception as e:
            logger.error(f"OCR extraction failed for {image_path}: {e}")
            return ""

    def analyze_screenshot(self, image_path: str, ocr_text: str = "", app_info: Dict[str, str] = None, previous_context: str = "") -> str:
        """Sends the screenshot to Vertex AI to deduce the user's action."""
        if not self.client:
            return "AI analysis disabled."
            
        app_info = app_info or {"app": "Unknown", "window_title": "Unknown"}
        
        # OmniParser Integration
        ui_context = "No specific UI elements detected."
        if config.OMNIPARSER_ENABLED:
            from src.core.omniparser_detector import OmniParserDetector
            detector = OmniParserDetector()
            detections = detector.parse(image_path)
            if detections:
                items = [f"[{d['id']}] {d['label']} at {d['box']}" for d in detections]
                ui_context = "; ".join(items)
        
        context_str = previous_context if previous_context else ""
        
        prompt = f"""
        Your goal is NOT to describe every screenshot.
        Your goal is to identify meaningful workflow milestones.

        Ignore:
        - Loading screens
        - Hover actions
        - Duplicate screens
        - Minor UI changes
        - Transitional states

        Only report actions that advance the user's workflow.

        ### INPUT CONTEXT:
        - **Active Application**: {app_info.get('app', 'Unknown')}
        - **Window Title**: {app_info.get('window_title', 'Unknown')}
        - **OCR Extracted Text**: {ocr_text}
        - **Detected UI Elements**: {ui_context}
        - **Preceding Workflow History**:
        {context_str if context_str.strip() else "- SESSION START: No prior actions. This is the first captured frame."}

        ### CORE ANALYSIS RULES:

        **Rule 1: Ignore Loading Screens**
        Do NOT generate workflow events for:
        - Loading indicators
        - Skeleton loaders
        - Progress bars
        - Spinners
        - Placeholder content
        - Browser startup screens
        - Empty tabs
        - Splash screens
        If the screenshot primarily shows a loading state, return EXACTLY:
        IGNORE_SCREENSHOT

        **Rule 2: Ignore Duplicate Screens**
        If the current screenshot represents the same page, application state, or workflow step as the previous screenshot, return EXACTLY:
        IGNORE_SCREENSHOT
        Only create an event when a meaningful state transition occurs.

        **Rule 3: Ignore Hover Events**
        Do not treat cursor hovering as a workflow action.
        Examples to ignore:
        - Hovering buttons
        - Hovering links
        - Hovering playlists
        - Hovering menu items
        Only report actual actions such as:
        - Click
        - Navigation
        - Page load completion
        - Form submission
        - Data creation
        - File upload
        - Playback start
        - Playback pause

        **Rule 4: Focus on Business Actions**
        Describe only meaningful user intent and outcomes.
        Good: "User copied transcript share link."
        Good: "Meeting summary loaded successfully."
        Bad: "Cursor hovered over Share button."
        Bad: "User positioned cursor over playlist item."

        **Rule 5: Detect Stable Screens**
        Only generate a screenshot description if the screen has remained visually stable for at least 1-2 seconds after a detected change.
        Ignore transient intermediate states.

        **Rule 6: One Event Per Workflow Step**
        Combine related screenshots into a single workflow action.
        Example:
        Open Chrome -> Loading page -> Meeting summary appears
        Output: "User opened shared transcript link and reviewed meeting summary."
        Do not create separate events for intermediate loading states.

        Based on the screenshot, OCR text, and preceding workflow history, produce the next entry in the continuous activity log.
        """
        
        max_retries = 3
        retry_delay = 10
        
        contents = [prompt]
        annotated_path = config.ANNOTATED_DIR / f"annotated_{Path(image_path).name}"
        img_to_analyze = str(annotated_path) if annotated_path.exists() else image_path
        
        try:
            img = Image.open(img_to_analyze)
            contents.append(img)
        except Exception as e:
            logger.error(f"Failed to open image {img_to_analyze}: {e}")
            return "Error: Cannot open image."
            
        crop_path = config.ANNOTATED_DIR / f"crop_{Path(image_path).name}"
        if crop_path.exists():
            try:
                crop_img = Image.open(str(crop_path))
                contents.append(crop_img)
            except:
                pass
                
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents
                )
                return response.text.strip()
                
                # logger.info(f"Sending screenshot {image_path} to Ollama for analysis...")
                # images_to_send = [img_to_analyze]
                # crop_path = config.ANNOTATED_DIR / f"crop_{Path(image_path).name}"
                # if crop_path.exists():
                #     images_to_send.append(str(crop_path))
                    
                # response = ollama.chat(
                #     model=self.vision_model,
                #     messages=[{
                #         'role': 'user',
                #         'content': prompt,
                #         'images': images_to_send
                #     }]
                # )
                # logger.info(f"Successfully received analysis for {image_path}")
                # return response['message']['content'].strip()
                
            except Exception as e:
                error_msg = str(e)
                if ("connection" in error_msg.lower() or "timeout" in error_msg.lower()) and attempt < max_retries - 1:
                    logger.warning(f"Connection issue. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"Error during AI analysis: {e}")
                    return f"Error: {error_msg}"
                
        return "Error: Max retries exceeded."

    def analyze_full(self, filepath: str, previous_context: str = "") -> Dict[str, str]:
        """Convenience method combining OCR and Vision."""
        ocr_text = self.extract_text(filepath)
        
        ui_elements_text = ""
        if config.OMNIPARSER_ENABLED:
            from src.core.omniparser_detector import OmniParserDetector
            detector = OmniParserDetector()
            detections = detector.parse(filepath)
            if detections:
                ui_elements_text = "; ".join([f"[{d['id']}] {d['label']} at {d['box']}" for d in detections])
                
        ai_description = self.analyze_screenshot(filepath, ocr_text=ocr_text, previous_context=previous_context)
        return {
            "ocr_text": ocr_text,
            "ai_description": ai_description,
            "ui_elements": ui_elements_text
        }

    def analyze_session_batch(self, screenshots: List[Dict[str, Any]], ocr_map: Optional[Dict[int, str]] = None) -> List[Dict[str, Any]]:
        """Processes an entire batch of screenshots in chunks to deduplicate based on global context."""
        if not self.client or not screenshots:
            return [{"id": ss["id"], "ai_description": "AI analysis disabled."} for ss in screenshots]

        ocr_map = ocr_map or {}
        chunk_size = 20
        all_results = []
        ui_map = {}
        previous_summary = "None. This is the start of the session."

        for i in range(0, len(screenshots), chunk_size):
            chunk = screenshots[i:i + chunk_size]
            
            prompt = f"""
            You are a Senior Technical Business Analyst at a Multinational Corporation (MNC). You are given a chronological chunk of screenshots representing part of a technical product demonstration or project session.
            
            **PREVIOUS CONTEXT / SESSION HISTORY SO FAR:**
            {previous_summary}
            
            Your task is to filter screenshots and retain ONLY screenshots that represent meaningful technical product features, architectural workflows, configuration states, or demonstrations of business value.

            GOAL:
            Create a production-grade MNC technical activity timeline that highlights only the key product demonstration steps.

            KEEP screenshots if they show:
            1. Technical Product Features (Dashboards, UI flows, data tables, module overviews)
            2. System Architectures & Workflows (Diagrams, system configurations, technical settings)
            3. Development/Code States (Code blocks, terminals, API interfaces, structural code)
            4. Meaningful Application States (Final outputs, successful workflows, error logs)

            CRITICAL MEETING UI INSTRUCTION:
            If this is a video meeting (e.g., Google Meet, Zoom, Teams), you MUST visually ignore the meeting wrapper (e.g., participant grids, chat boxes, "You are presenting" overlays, recording controls) and EXCLUSIVELY describe the technical product being shared on the screen. Do NOT describe the meeting interface itself.

            REMOVE screenshots if they show:
            - Loading screens, Splash screens, Blank pages, Page refreshes
            - Browser startup, New tab opening, URL typing
            - Navigation transitions, Window/Tab switching
            - Screen sharing controls, Mic mute/unmute, Camera on/off, Meeting controls
            - Notification popups, Cursor-only actions
            - Duplicate screens, Screens with >90% visual similarity
            - Idle screens, Waiting states
            - Application launch screens, Login redirects
            - Music players, Non-work-related content
            - Screens that do not advance the workflow
            - Login pages, Authentication screens, Password entry forms
            - Empty meeting lobbies, "Waiting for Host" screens, or meeting screens where NO product is being shared
            - CRITICAL: Self-Referential UI (The "AI Screen Activity Analyzer" app itself, recording controls, overlays)

            IMPORTANT RULES:
            1. Prefer outcome over transition (e.g., Keep "Agent Configuration Page Displayed", Remove "Opening Agents Page").
            2. Prefer completed action over preparation (e.g., Keep "Meeting Summary Displayed", Remove "Typing URL").
            3. Prefer business value over technical events (e.g., Keep "Thunai Dashboard Presented", Remove "Started Screen Share").
            4. Remove screenshots whose absence would not reduce understanding of the workflow.

            **Output Rules for Ignored Frames:**
            If a screenshot should be REMOVED based on the rules above, its description MUST be EXACTLY "IGNORE_SCREENSHOT".
            Only provide a description for screenshots you choose to KEEP.
            
            **Self-Referential UI Rule:**
            CRITICAL: If a screenshot displays a screen recording application, recording controls, recording overlays, monitoring dashboards, or any screen-capture software UI (including the "AI Screen Activity Analyzer" app itself), you MUST return EXACTLY "IGNORE_SCREENSHOT". Do not describe the user interacting with the recording tool; these do not represent actual work.
            
            **Output JSON Structure:**
            You MUST output a valid JSON object with exactly two keys. Do not use Markdown wrappers like ```json. Just raw JSON.
            - "results": A JSON array where each object has "id" (the integer ID of the screenshot) and "description" (The precise action with duration, or "IGNORE_SCREENSHOT").
            - "new_summary": A concise 1-2 sentence string summarizing the entire flow up to this point (incorporating the previous context + this chunk) to pass to the next chunk.
            
            Analyze the images and text below and return the JSON object.
            """

            contents = [prompt]
            
            for ss in chunk:
                try:
                    img = Image.open(ss["filepath"])
                    timestamp = ss.get("timestamp", "Unknown")
                    ocr_text = ocr_map.get(ss["id"], "")
                    
                    text_context = f"Screenshot ID: {ss['id']} | Timestamp: {timestamp}"
                    if ocr_text:
                        text_context += f"\nExtracted Text: {ocr_text[:500]}..." # Truncate to save tokens
                        
                    if config.OMNIPARSER_ENABLED:
                        from src.core.omniparser_detector import OmniParserDetector
                        detector = OmniParserDetector()
                        detections = detector.parse(ss["filepath"])
                        if detections:
                            ui_str = "; ".join([f"[{d['id']}] {d['label']} at {d['box']}" for d in detections])
                            text_context += f"\nDetected Elements: {ui_str}"
                            ui_map[ss["id"]] = ui_str
                    
                    contents.append(text_context)
                    contents.append(img)
                except Exception as e:
                    logger.error(f"Failed to load image for batch analysis: {ss['filepath']}")
                    
            try:
                from google.genai import types
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=BatchResponseSchema
                    )
                )
                
                result_json = json.loads(response.text)
                
                # Update rolling summary for the next chunk
                previous_summary = result_json.get("new_summary", previous_summary)
                
                # Map results back for this chunk
                results_array = result_json.get("results", [])
                desc_map = {item["id"]: item["description"] for item in results_array if "id" in item}
                
                for ss in chunk:
                    all_results.append({
                        "id": ss["id"],
                        "ai_description": desc_map.get(ss["id"], "IGNORE_SCREENSHOT"),
                        "ui_elements": ui_map.get(ss["id"], "")
                    })
                    
            except Exception as e:
                logger.error(f"Batch analysis failed for chunk: {e}")
                for ss in chunk:
                    all_results.append({"id": ss["id"], "ai_description": f"Error: {e}"})
                    
        return all_results

    def filter_and_summarize_workflow(self, timeline_events: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
        """Generates a comprehensive summary and filters out low-value screenshots."""
        if not self.client:
            return timeline_events, "Session Summary: AI analysis disabled."
        if not timeline_events:
            return timeline_events, "Session Summary: No activity recorded."

        timeline_str = ""
        for event in timeline_events[:200]:
            if "gemini_observation" in event:
                timeline_str += f"[ID: {event.get('screenshot_id', 'N/A')}] {event['timestamp']} - {event.get('app', 'System')} - {event['gemini_observation']}\n"
            else:
                timeline_str += f"[ID: N/A] {event['timestamp']} - {event.get('app', 'System')} ({event.get('window_title', '')}) - Action: {event.get('event', 'interaction')}\n"

        prompt = f"""
        You are a Senior Technical Writer and Workflow Analyst at an MNC. You are given a raw chronological timeline of user activities, which includes screen captures (with IDs) and text-based actions from a recorded meeting or product demonstration.
        
        Your objective is to transform this raw log into a professional Technical Session Document. A stakeholder who did not attend the meeting should be able to read your report and completely understand the technical product demonstrated, the architectures shown, and the workflows executed.

        Your task is two-fold:
        1. Evaluate the importance of each screenshot ID. Aggressively filter out repetitive screenshots, non-technical transitions, and minor UI states.
        CRITICAL RULE: You MUST strictly exclude and NEVER retain any screenshot IDs that show the user interacting with the screen recording software itself.
        
        2. For the screenshots you CHOOSE TO RETAIN, you must rewrite their descriptions. Do NOT write short robotic descriptions. INSTEAD, write naturally and technically: Describe the system component, the workflow being demonstrated, and the configuration state. (e.g., "The presenter demonstrated the Thunai AI Knowledge Base dashboard, highlighting the vector database configuration and document ingestion pipeline.")

        3. Generate a highly detailed Technical Session Summary.
        The summary MUST explain: The technical product demonstrated, system architectures discussed, core workflows shown, and the final state.

        CRITICAL FORMATTING INSTRUCTIONS:
        You MUST output a structured JSON object containing "summary_blocks" and "retained_screenshots".
        Do NOT output a markdown string. Instead, break the report into logical blocks.
        Valid block types are: "h1", "h2", "h3", "paragraph", "list_item".

        Use the following structure for your blocks:
        - h1: "Technical Session Document"
        - paragraph: [A cohesive high-level executive summary of the technical demonstration]
        - h2: "Session Objective"
        - paragraph: [Clear statement of the technical goals achieved]
        - h2: "Technical Product Features Demonstrated"
        - list_item: "**[Feature Name]**: [Specific configurations or UI flows demonstrated]"
        - h2: "Architectures & Workflows Discussed"
        - list_item: [Architecture or Workflow 1]
        - list_item: [Architecture or Workflow 2]
        - h2: "Interface & Dashboard States"
        - h3: "Stage 1: [Stage Name]"
        - paragraph: "**Summary:** [What technical state was shown]"
        - h2: "Final Outcome"
        - paragraph: [Conclusion of the demonstration]
        - h2: "Session Metrics"
        - list_item: "**Total Technical Actions**: [Count]"
        - list_item: "**Total Workflow Stages**: [Count]"

        CRITICAL JSON FORMATTING RULES:
        1. You MUST output raw JSON without markdown wrappers.
        2. You MUST perfectly escape all double quotes inside your string values (e.g., "User clicked the \\"Save\\" button"). Failure to do so will break the JSON parser!
        3. Do not include unescaped control characters or unescaped newlines in your strings.

        You MUST output your response in raw JSON format with exactly two keys:
        {{
            "summary_blocks": [
                {{"type": "h1", "text": "Session Documentation Report"}},
                {{"type": "paragraph", "text": "This meeting..."}},
                {{"type": "h2", "text": "Meeting Objective"}},
                {{"type": "list_item", "text": "First item"}}
            ],
            "retained_screenshots": [
                {{"id": 12, "description": "The presenter navigated to the Thunai AI Knowledge Base..."}}
            ]
        }}

        Input Timeline Data:
        {timeline_str}
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SessionReportSchema
                )
            )
            result_text = response.text.strip()
            
            # Handle potential markdown wrappers if the model ignores the config
            if result_text.startswith("```json"):
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif result_text.startswith("```"):
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result_json = json.loads(result_text)
            
            summary = result_json.get("summary_blocks", result_json.get("summary", "Workflow summary could not be generated."))
            retained_list = result_json.get("retained_screenshots", [])
            
            # Create a map of retained IDs to their rewritten descriptions
            retained_map = {item["id"]: item.get("description", "") for item in retained_list if isinstance(item, dict) and "id" in item}
            
            # Filter and rewrite the timeline
            filtered_timeline = []
            for event in timeline_events:
                # If it's a screenshot event, check if its ID is in retained_map
                if "gemini_observation" in event:
                    ss_id = event.get("screenshot_id")
                    if ss_id in retained_map:
                        # Overwrite the original observation with the new story-driven description
                        event["gemini_observation"] = retained_map[ss_id]
                        filtered_timeline.append(event)
                else:
                    # Keep non-screenshot events
                    filtered_timeline.append(event)
                    
            return filtered_timeline, summary


        except Exception as e:
            err_msg = str(e)
            logger.error(f"Error generating session summary and filtering: {err_msg}")
            return timeline_events, f"Error generating summary: {err_msg}"
