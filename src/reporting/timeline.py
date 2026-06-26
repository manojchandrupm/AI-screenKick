from typing import List, Dict, Any

EVENT_DESCRIPTIONS = {
    "left_click": "Left clicked",
    "right_click": "Right clicked",
    "double_click": "Double clicked",
    "scroll": "Scrolled",
    "window_change": "Changed active window",
    "idle": "User went idle",
    "click": "Clicked"
}

def build_timeline(events: List[Dict[str, Any]], screenshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merges database events and screenshots into a single chronological timeline.
    Returns a sorted list of dictionaries.
    """
    timeline = []
    
    # Add events
    for ev in events:
        ev_type = ev.get("event_type", "")
        if ev_type not in EVENT_DESCRIPTIONS:
            continue
            
        desc = EVENT_DESCRIPTIONS[ev_type]
        timeline.append({
            "timestamp": ev.get("timestamp", ""),
            "event": ev_type,
            "action": desc,
            "x": ev.get("x"),
            "y": ev.get("y"),
            "window_title": ev.get("window_name", ""),
            "app": ev.get("window_name", ""), # legacy map
            "type": "event"
        })
        
    # Add screenshots
    for ss in screenshots:
        desc = ss.get("ai_description", "")
        if desc and desc.strip() != "IGNORE_SCREENSHOT":
            timeline.append({
                "screenshot_id": ss.get("id"),
                "timestamp": ss.get("timestamp", ""),
                "event": "screenshot_analyzed",
                "action": "AI Analysis",
                "gemini_observation": ss.get("ai_description"),
                "image_path": ss.get("filepath"),
                "annotated_path": ss.get("annotated_path"),
                "type": "ai_analysis"
            })
            
    # Sort chronologically
    timeline.sort(key=lambda x: x.get("timestamp", ""))
    return timeline
