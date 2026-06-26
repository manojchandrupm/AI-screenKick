import os
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from src.config import config

logger = logging.getLogger(__name__)

class ReportExporter:
    """Exports session data to PDF format."""

    def __init__(self):
        self.reports_dir = config.REPORTS_DIR

    def export_all(self, session: Dict[str, Any], timeline: List[Dict[str, Any]], summary: str) -> Dict[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        paths = {}
        paths["pdf"] = self._generate_pdf(session, summary, timeline, timestamp)
        return paths

    def _generate_pdf(self, session: Dict[str, Any], summary: str, timeline: List[Dict[str, Any]], timestamp: str) -> str:
        filepath = self.reports_dir / f"session_report_{timestamp}.pdf"
        try:
            doc = SimpleDocTemplate(str(filepath), pagesize=letter,
                                    rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Heading1'],
                fontSize=22,
                spaceAfter=6,
                textColor=colors.HexColor("#0f172a")
            )
            subtitle_style = ParagraphStyle(
                'ReportSubTitle',
                parent=styles['Normal'],
                fontSize=14,
                textColor=colors.HexColor("#64748b"),
                spaceAfter=20
            )
            section_header_style = ParagraphStyle(
                'SectionHeader',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor("#3b82f6"),
                spaceBefore=20,
                spaceAfter=10,
                textTransform='uppercase'
            )
            normal_style = styles['Normal']
            
            timeline_time_style = ParagraphStyle(
                'TimelineTime',
                parent=styles['Normal'],
                textColor=colors.HexColor("#3b82f6"),
                fontSize=10,
                fontName="Helvetica-Bold"
            )
            timeline_window_style = ParagraphStyle(
                'TimelineWindow',
                parent=styles['Normal'],
                textColor=colors.HexColor("#64748b"),
                fontSize=9
            )
            timeline_obs_style = ParagraphStyle(
                'TimelineObservation',
                parent=styles['Normal'],
                textColor=colors.HexColor("#0f172a"),
                fontSize=10,
                leftIndent=10
            )
            
            story = []
            
            # Header
            story.append(Paragraph("<b>AI SCREEN RECORDER</b>", title_style))
            story.append(Paragraph("Session Activity Report", subtitle_style))
            generated_str = datetime.now().strftime("%B %d, %Y at %H:%M")
            story.append(Paragraph(f"Generated: {generated_str}", normal_style))
            story.append(Spacer(1, 20))
            
            # Stats Table
            start_dt = session.get('start_time', '')
            end_dt = session.get('end_time', '')
            if start_dt:
                start_dt = start_dt[:19].replace('T', ' ')
            if end_dt:
                end_dt = end_dt[:19].replace('T', ' ')
            
            # calculate duration in seconds
            dur_str = "0s"
            if session.get('start_time') and session.get('end_time'):
                try:
                    s_t = datetime.fromisoformat(session['start_time'])
                    e_t = datetime.fromisoformat(session['end_time'])
                    dur_secs = int((e_t - s_t).total_seconds())
                    dur_str = f"{dur_secs}s"
                except:
                    pass
            
            total_events = str(len([e for e in timeline if e.get("type") == "event"]))
            total_screenshots = str(len([e for e in timeline if e.get("type") == "ai_analysis"]))
            total_steps = str(len(timeline))
            
            data = [
                ['Start Time', 'End Time', 'Duration'],
                [start_dt, end_dt, dur_str],
                ['Total Events', 'Screenshots', 'Timeline Steps'],
                [total_events, total_screenshots, total_steps]
            ]
            
            t = Table(data, colWidths=[170, 170, 170])
            t.setStyle(TableStyle([
                ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#0f172a")),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTNAME', (0,2), (-1,2), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('LINEBELOW', (0,1), (-1,1), 1, colors.HexColor("#e2e8f0")),
            ]))
            story.append(t)
            story.append(Spacer(1, 20))
            
            # Summary Section
            story.append(Paragraph("AI SESSION SUMMARY", section_header_style))
            
            def process_inline_markdown(text: str) -> str:
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'(?<!\S)\*(.*?)\*(?!\S)', r'<i>\1</i>', text)
                text = text.replace('<', '&lt;').replace('>', '&gt;')
                text = text.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
                text = text.replace('&lt;i&gt;', '<i>').replace('&lt;/i&gt;', '</i>')
                return text

            # Enhanced parser for the new LLM structure
            if isinstance(summary, str) and summary.strip().startswith('['):
                try:
                    summary = json.loads(summary)
                except Exception:
                    pass

            if not summary or (isinstance(summary, str) and ("Error" in summary or "disabled" in summary.lower())):
                story.append(Paragraph(summary if isinstance(summary, str) else "No summary generated.", normal_style))
                story.append(Spacer(1, 20))
            elif isinstance(summary, list):
                # New structured blocks format
                for block in summary:
                    b_type = block.get("type", "paragraph")
                    text = block.get("text", "")
                    if not text: continue
                    
                    if b_type == "h1":
                        story.append(Spacer(1, 12))
                        story.append(Paragraph(process_inline_markdown(text), title_style))
                        story.append(Spacer(1, 6))
                    elif b_type == "h2":
                        story.append(Spacer(1, 8))
                        story.append(Paragraph(process_inline_markdown(text), section_header_style))
                        story.append(Spacer(1, 4))
                    elif b_type == "h3":
                        story.append(Spacer(1, 8))
                        story.append(Paragraph(f"<b>{process_inline_markdown(text)}</b>", normal_style))
                    elif b_type == "list_item":
                        story.append(Paragraph(f"&bull; {process_inline_markdown(text)}", normal_style))
                        story.append(Spacer(1, 4))
                    else: # paragraph
                        story.append(Paragraph(process_inline_markdown(text), normal_style))
                        story.append(Spacer(1, 6))
                story.append(Spacer(1, 20))
            else:
                # Legacy string format
                for p in summary.split('\n'):
                    p = p.strip()
                    if not p: continue
                    
                    if p.startswith('# '):
                        story.append(Spacer(1, 12))
                        story.append(Paragraph(process_inline_markdown(p[2:]), title_style))
                        story.append(Spacer(1, 6))
                    elif p.startswith('## '):
                        story.append(Spacer(1, 8))
                        story.append(Paragraph(process_inline_markdown(p[3:]), section_header_style))
                        story.append(Spacer(1, 4))
                    elif p.startswith('### '):
                        story.append(Spacer(1, 8))
                        story.append(Paragraph(f"<b>{process_inline_markdown(p[4:])}</b>", normal_style))
                    else:
                        if p.startswith('- ') or p.startswith('* '):
                            p = "&bull; " + p[2:]
                        story.append(Paragraph(process_inline_markdown(p), normal_style))
                        story.append(Spacer(1, 4))
                story.append(Spacer(1, 20))
            
            # Timeline Section
            story.append(Paragraph("ACTIVITY TIMELINE", section_header_style))
            
            for event in timeline:
                ev_type = event.get("type", "")
                time_str = event.get("timestamp", "")
                if time_str:
                    try:
                        time_obj = datetime.fromisoformat(time_str)
                        time_str = time_obj.strftime("%I:%M:%S %p")
                    except:
                        time_str = time_str[11:19]
                        
                if ev_type == "event":
                    action = event.get("action", "")
                    window = event.get("window", "")
                    story.append(Paragraph(f"{time_str} &middot; {action}", timeline_time_style))
                    if window:
                        story.append(Paragraph(f"Window: {window}", timeline_window_style))
                    story.append(Spacer(1, 10))
                    
                elif ev_type == "ai_analysis":
                    trigger = event.get("trigger_type", "auto")
                    obs = event.get("gemini_observation", "")
                    img_path = event.get("annotated_path") or event.get("image_path", "")
                    
                    story.append(Paragraph(f"{time_str} &middot; Auto capture ({trigger})", timeline_time_style))
                    if obs:
                        story.append(Paragraph(f"<b>F</b> {process_inline_markdown(obs)}", timeline_obs_style))
                    story.append(Spacer(1, 6))
                    
                    if img_path and os.path.exists(img_path):
                        try:
                            # Constrain image size
                            img = RLImage(img_path, width=400, height=225, kind='proportional')
                            story.append(img)
                        except Exception as e:
                            logger.error(f"Failed to embed image in PDF: {e}")
                            
                    story.append(Spacer(1, 15))
                    
            doc.build(story)
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            return ""
