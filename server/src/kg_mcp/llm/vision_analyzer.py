"""
Vision Analyzer - Extracts structured life events from screenshots or text.
"""
import json
import logging
from datetime import datetime
from typing import Optional

from litellm import acompletion

from kg_mcp.life.analysis_schema import LifeEventAnalysis, EventCandidate
from kg_mcp.life.event_taxonomy import EVENT_TYPES
from kg_mcp.config import get_settings

logger = logging.getLogger(__name__)

EVENT_TYPE_LIST = ", ".join(EVENT_TYPES)

ANALYSIS_PROMPT = """You extract useful work context from an explicitly shared screenshot.

Context:
- Timestamp: {timestamp}
- Active App: {app}
- Window Title: {window}
- Previous Context: {previous_context}

Extract only the minimum information needed to recall the activity.

EXTRACTION PRIORITIES BY APP TYPE:

**Video Calls (Teams, Zoom, Meet, Slack Huddle):**
- Describe the meeting topic without transcribing participant lists or messages
- Meeting title/subject if shown
- Duration/time indicators
- Chat messages visible
- Screen sharing content if any

**Email (Outlook, Gmail, Mail):**
- Do not copy email addresses, recipients, or message bodies
- Subject line
- Key content phrases
- Attachments mentioned

**Documents (Word, Google Docs, Pages, PDF):**
- Document title
- Author if visible
- Section headings
- Topic-level summary only
- Comments/suggestions visible

**Browser/Web:**
- Full URL if visible
- Page title
- Key headings and content
- Never extract form values

**IDE/Code (VS Code, Xcode, IntelliJ):**
- Open file path
- Function/class names visible
- Error messages
- High-level development activity, excluding terminal secrets and environment values

**Chat/Messaging (Slack, Discord, WhatsApp):**
- Channel/conversation name
- Conversation topic only, without authors or message content
- Mentioned people/topics

Return ONLY a JSON object with EXACT structure:
{{
  "ts": "{timestamp}",
  "active_app": "{app}",
  "window_title": "{window}",
  "artifact": {{
    "type": "meeting|web|doc|email|ticket|chat|sheet|ide|calendar|unknown",
    "canonical_id": "unique identifier (URL, file path, meeting ID, etc)",
    "title": "document/meeting/page title",
    "url_or_path": "full URL or file path if visible",
    "owner_org": "organization name if identifiable"
  }},
  "event_candidates": [
    {{"type": "EVENT_TYPE", "confidence": 0.0-1.0}}
  ],
  "visible_text_snippets": [
    {{"text": "exact text from screen", "source": "where it appears", "confidence": 0.9}}
  ],
  "entities": [
    {{"kind": "person|organization|ticket|task|file|email|url|meeting", "value": "exact value", "role": "participant|author|recipient|assignee|etc", "confidence": 0.9}}
  ],
  "concepts": [
    {{"label": "topic/theme", "confidence": 0.8}}
  ],
  "meeting_details": {{
    "title": "meeting subject if applicable",
    "participants": ["list of ALL visible participant names"],
    "duration": "if visible",
    "is_recording": false
  }},
  "sentiment_or_state": {{
    "blocker": false,
    "urgency": 0.0-1.0,
    "activity_type": "active_work|passive_viewing|communication|idle"
  }}
}}

CRITICAL RULES:
- Never extract passwords, tokens, API keys, personal messages, email addresses or form values.
- Prefer summaries over verbatim text. Omit uncertain or sensitive details.
- Keep people and organization entities empty unless the user explicitly supplied them as context.
- Event types: {event_types}
- DO NOT summarize. EXTRACT verbatim.
"""


TEXT_ANALYSIS_PROMPT = """You are analyzing text typed by the user to build a structured activity memory.

Context:
- Timestamp: {timestamp}
- App: {app}

Text Content:
{text_content}

Return ONLY a JSON object with the EXACT structure described below (include all fields even if empty):
{{
  "ts": "{timestamp}",
  "active_app": "{app}",
  "window_title": "",
  "artifact": {{
    "type": "web|doc|email|ticket|chat|sheet|ide|unknown",
    "canonical_id": "string",
    "title": "string",
    "url_or_path": "string",
    "owner_org": "string|null"
  }},
  "event_candidates": [
    {{"type": "ARTIFACT_EDIT", "confidence": 0.0}}
  ],
  "visible_text_snippets": [
    {{"text": "string", "confidence": 0.0}}
  ],
  "entities": [
    {{"kind": "person|organization|ticket|task|file|unknown", "value": "string", "confidence": 0.0}}
  ],
  "concepts": [
    {{"label": "string", "confidence": 0.0}}
  ],
  "sentiment_or_state": {{
    "blocker": false,
    "urgency": 0.0
  }}
}}

Rules:
- Use ONLY these event types: {event_types}.
- Prioritize TODOs, decisions, blockers if present in text.
- Never reproduce passwords, tokens, API keys, email addresses or other credentials.
- Do not include any extra keys or markdown.
"""


def _coerce_analysis(data: dict, app: str, window: str, timestamp: str) -> LifeEventAnalysis:
    analysis = LifeEventAnalysis(**(data or {}))
    updates = {}
    if not analysis.ts:
        updates["ts"] = timestamp
    if not analysis.active_app:
        updates["active_app"] = app
    if not analysis.window_title:
        updates["window_title"] = window
    if updates:
        analysis = analysis.model_copy(update=updates)
    return analysis


async def analyze_screenshot(
    screenshot_base64: str,
    app: str,
    window: str = "",
    previous_context: str = "",
    model: str = None,
) -> LifeEventAnalysis:
    """
    Analyze a screenshot using Gemini Vision via LiteLLM gateway.
    """
    settings = get_settings()
    if model is None:
        model = settings.litellm_model if settings.llm_mode == "litellm" else settings.gemini_model
        model = model or settings.llm_model

    noise_apps = {"Finder", "loginwindow", "universalAccessAuthWarn", "SystemUIServer"}
    if app in noise_apps:
        return LifeEventAnalysis(
            ts=datetime.now().isoformat(),
            active_app=app,
            window_title=window,
            event_candidates=[EventCandidate(type="IDLE", confidence=1.0)],
        )

    timestamp = datetime.now().isoformat()
    prompt = ANALYSIS_PROMPT.format(
        app=app,
        window=window or "(no title)",
        previous_context=previous_context or "None",
        timestamp=timestamp,
        event_types=EVENT_TYPE_LIST,
    )

    try:
        completion_kwargs = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{screenshot_base64}"},
                        },
                    ],
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.1,
        }

        if settings.llm_mode == "litellm" and settings.litellm_base_url:
            completion_kwargs["api_base"] = settings.litellm_base_url
            completion_kwargs["api_key"] = settings.litellm_api_key
            completion_kwargs["custom_llm_provider"] = "openai"  # Treat gateway as OpenAI-compatible
        elif settings.gemini_api_key:
            # Pass API key for direct Gemini calls
            completion_kwargs["api_key"] = settings.gemini_api_key

        response = await acompletion(**completion_kwargs)
        raw_text = response.choices[0].message.content or ""

        json_text = raw_text
        if "```json" in raw_text:
            import re
            match = re.search(r"```json\s*([\s\S]*?)```", raw_text)
            if match:
                json_text = match.group(1)
        if "{" in json_text:
            start = json_text.find("{")
            end = json_text.rfind("}")
            if start != -1 and end != -1:
                json_text = json_text[start:end + 1]

        data = json.loads(json_text.strip())
        return _coerce_analysis(data, app, window, timestamp)

    except Exception as e:
        logger.error(f"Screenshot analysis failed: {e}")
        return LifeEventAnalysis(
            ts=datetime.now().isoformat(),
            active_app=app,
            window_title=window,
            event_candidates=[EventCandidate(type="IDLE", confidence=1.0)],
        )


async def analyze_text_content(
    text_content: str,
    app: str,
    model: str = None,
) -> LifeEventAnalysis:
    """
    Analyze text content using LLM and return structured event schema.
    """
    settings = get_settings()
    if model is None:
        model = settings.litellm_model if settings.llm_mode == "litellm" else settings.gemini_model
        model = model or settings.llm_model

    timestamp = datetime.now().isoformat()
    prompt = TEXT_ANALYSIS_PROMPT.format(
        app=app,
        timestamp=timestamp,
        text_content=text_content,
        event_types=EVENT_TYPE_LIST,
    )

    try:
        completion_kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500,
            "temperature": 0.1,
        }

        if settings.llm_mode == "litellm" and settings.litellm_base_url:
            completion_kwargs["api_base"] = settings.litellm_base_url
            completion_kwargs["api_key"] = settings.litellm_api_key
            completion_kwargs["custom_llm_provider"] = "openai"  # Treat gateway as OpenAI-compatible
        elif settings.gemini_api_key:
            # Pass API key for direct Gemini calls
            completion_kwargs["api_key"] = settings.gemini_api_key

        response = await acompletion(**completion_kwargs)
        raw_text = response.choices[0].message.content or ""

        json_text = raw_text
        if "```json" in raw_text:
            import re
            match = re.search(r"```json\s*([\s\S]*?)```", raw_text)
            if match:
                json_text = match.group(1)
        if "{" in json_text:
            start = json_text.find("{")
            end = json_text.rfind("}")
            if start != -1 and end != -1:
                json_text = json_text[start:end + 1]

        data = json.loads(json_text.strip())
        return _coerce_analysis(data, app, "", timestamp)

    except Exception as e:
        logger.error(f"Text analysis failed: {e}")
        return LifeEventAnalysis(
            ts=timestamp,
            active_app=app,
            window_title="",
            event_candidates=[EventCandidate(type="IDLE", confidence=1.0)],
        )


def analysis_to_dict(analysis: LifeEventAnalysis) -> dict:
    """Convert LifeEventAnalysis to dict for storage."""
    return analysis.model_dump()
