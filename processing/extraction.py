import requests
import json
from datetime import datetime
from typing import Optional, Dict, Any


class EventExtractor:
    """
    Modular event extractor using a local LLM (Mistral via Ollama).
    Can be extended to support other models by subclassing or replacing the _query_model method.
    """

    def __init__(
        self, model_endpoint: str = "http://localhost:11434/api/generate"
    ):
        self.model_endpoint = model_endpoint

    def extract_event(self, text: str) -> Dict[str, Any]:
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
        # Get current date and time
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        return f'''
The current date and time is: {current_time}

Only consider the following event categories:
- Conflict and protests
- Climate-related events (e.g., floods, droughts, storms)
- Health outbreaks and emergencies
- Infrastructure disruptions that can affect pedestrians or vehicles (e.g., outages, road collapses)
- Crime incidents
- Cultural or tourist events
- No event (if no real-world event is described or if it has already passed and is no longer relevant)

For each input text, extract the following information in valid JSON:
- "event_type": One of the categories above
- "city": The city where the event is taking place
- "location": The most accurate location mentioned. Best would be the specific address of the event, or the venue if it is mentioned. If an area is referred to the event, use the area's name.
- "date": The **exact date** when the event is occurring or is expected to occur (format: YYYY-MM-DD). If the event is upcoming or ongoing, reflect the precise date as mentioned in the text. If the event has no specified date but only a rough estimate (like "tomorrow" or "next week"), try to infer a plausible date.
- "time": The **exact time** when the event is occurring or is expected to occur (format: HH:MM). If the event is ongoing or upcoming and time is mentioned, reflect it. If no time is specified but vague time references are given (like "morning," "afternoon," or "evening"), infer a time such as 10:00, 15:00, or 19:00 respectively. If no time is specified, set it to **null**.
- "summary": A one-sentence summary of the event, written clearly for someone scanning events on a map.

If the text describes an event **in the past** (using past tense verbs or referring to something already happened), return:

{{
  "event_type": "No event",
  "city": null,
  "location": null,
  "date": null,
  "time": null,
  "summary": "No real-world event found."
}}

Only include events that are **ongoing** or **upcoming** that are relevant for the user, such as helping them decide where to go or avoid. If the text does not describe such an event, return:

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
