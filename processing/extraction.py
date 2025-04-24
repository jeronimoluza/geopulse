import requests
import json
from typing import Dict, Any, Optional, Tuple
from .pre_filter import PreFilter


class EventExtractor:
    """
    Modular event extractor using a local LLM (Mistral via Ollama).
    Can be extended to support other models by subclassing or replacing the _query_model method.
    """

    def __init__(
        self, model_endpoint: str = "http://localhost:11434/api/generate",
        use_pre_filter: bool = True
    ):
        self.model_endpoint = model_endpoint
        self.use_pre_filter = use_pre_filter
        if use_pre_filter:
            self.pre_filter = PreFilter(model_endpoint)

    def extract_event(self, text: str, title: str = "", subtitle: str = "") -> Dict[str, Any]:
        if self.use_pre_filter and title:
            should_process, reason = self.pre_filter.should_process(title, subtitle)
            if not should_process:
                return {
                    "event_type": "No event",
                    "city": None,
                    "location": None,
                    "date": None,
                    "time": None,
                    "summary": f"Filtered out: {reason}"
                }
        
        prompt = self._build_prompt(text)
        try:
            response = self._query_model(prompt)
            data = self._parse_response(response)
            return data
        except Exception as e:
            print(e)
            # Fallback: No event
            return {
                "event_type": "No event",
                "location": None,
                "date": None,
                "time": None,
                "summary": "No real-world event found.",
            }

    def _build_prompt(self, input_text: str) -> str:
        return f'''
You are an event extractor that processes news articles to identify real-world events that are currently happening or are about to happen. Your goal is to extract structured, geolocated information that can be used to power a live event map.

You focus only on physical events that occur at a specific place and time, and that could help a person decide where to go or what to avoid — such as conflicts, cultural gatherings, climate disruptions, infrastructure issues, or public safety incidents.

You must ignore:

Administrative announcements (e.g., subscription openings, academic calendar updates)

Policy statements or press releases with no immediate physical effect

Obituaries or news of someone’s passing

Events that occurred entirely in the past

You prioritize accuracy, time relevance, and clarity for users monitoring real-time urban activity.

Only consider the following event categories:
- Conflict and protests
- Climate-related events (e.g., floods, droughts, storms)
- Health outbreaks and emergencies
- Infrastructure disruptions that can affect pedestrians or vehicles (e.g., outages, road collapses)
- Crime incidents
- Cultural or tourist events
- No event (if no real-world event is described)

For each input text, extract the following information in valid JSON:
- "event_type": One of the categories above
- "city": The city where the event is taking place
- "location": The most accurate location mentioned. Best would be the specific address of the event, or the venue if it is mentioned. If an area is referred to the event, use the area's name.
- "date": The **exact date** when the event is occurring or is expected to occur (format: YYYY-MM-DD). If the event is upcoming or ongoing, reflect the precise date as mentioned in the text. If the event has no specified date but only a rough estimate (like "tomorrow" or "next week"), try to infer a plausible date.
- "time": The **exact time** when the event is occurring or is expected to occur (format: HH:MM). If the event is ongoing or upcoming and time is mentioned, reflect it. If no time is specified but vague time references are given (like "morning," "afternoon," or "evening"), infer a time such as 10:00, 15:00, or 19:00 respectively. If no time is specified, set it to **null**.
- "summary": A one-sentence summary of the event, written clearly for someone scanning events on a map.

If no event is mentioned, return:

{{
  "event_type": "No event",
  "city": null,
  "location": null,
  "date": null,
  "time": null,
  "summary": "No real-world event found."
}}

Now extract the event from the following text:

"""
{input_text}
"""
'''

    def _query_model(self, prompt: str) -> str:
        payload = {"model": "mistral", "prompt": prompt, "stream": False}
        headers = {"Content-Type": "application/json"}
        resp = requests.post(
            self.model_endpoint,
            data=json.dumps(payload),
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        # Ollama returns a JSON with a 'response' field containing the model output
        return resp.json().get("response", "")

    def _parse_response(self, response: str) -> Dict[str, Any]:
        try:
            # Try to extract the first JSON block from the response
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
            data = json.loads(json_str)
            # Validate fields
            for field in ["event_type", "city", 'location', "date", "time", "summary"]:
                if field not in data:
                    raise ValueError(f"Missing field: {field}")
            return data
        except Exception:
            # Fallback: No event
            return {
                "event_type": "No event",
                "city": None,
                "location": None,
                "date": None,
                "time": None,
                "summary": "No real-world event found.",
            }
