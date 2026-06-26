import logging

logger = logging.getLogger(__name__)

class PrivacyFilter:
    """Heuristic filter to identify and reject sensitive or irrelevant screens."""
    
    # Keywords indicating a login or authentication page
    LOGIN_KEYWORDS = [
        "sign in", "log in", "password", "forgot password", 
        "username", "enter your credentials", "authenticate"
    ]
    
    # Keywords indicating an empty video meeting lobby or waiting state
    MEETING_KEYWORDS = [
        "waiting for the host to start", 
        "ready to join?", 
        "no one else is here",
        "you're in a waiting room"
    ]

    @classmethod
    def is_blacklisted(cls, ocr_text: str, window_title: str = "") -> bool:
        """
        Returns True if the screen is identified as a login page or meeting share.
        """
        text_lower = ocr_text.lower()
        title_lower = window_title.lower() if window_title else ""
        
        # Check window title for meetings
        if "meet -" in title_lower or "zoom meeting" in title_lower:
            logger.info("PrivacyFilter: Blacklisted via window title (Meeting detected).")
            return True
            
        # Check OCR for login forms
        for kw in cls.LOGIN_KEYWORDS:
            if kw in text_lower:
                logger.info(f"PrivacyFilter: Blacklisted via OCR (Login detected: '{kw}').")
                return True
                
        # Check OCR for meeting screens
        for kw in cls.MEETING_KEYWORDS:
            if kw in text_lower:
                logger.info(f"PrivacyFilter: Blacklisted via OCR (Meeting detected: '{kw}').")
                return True
                
        return False
