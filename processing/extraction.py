import requests
import json
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
                "summary": "No real-world event found.",
            }

    def _build_prompt(self, input_text: str) -> str:
        return f'''
You are an event extractor for a geospatial event mapping system. Your task is to read short news articles or tweets and extract structured information about real-world events.

Only consider the following event categories:
- Conflict and protests
- Climate-related events (e.g., floods, droughts, storms)
- Health outbreaks and emergencies
- Infrastructure disruptions (e.g., outages, road collapses)
- Crime incidents
- Cultural or public events
- No event (if no real-world event is described)

For each input text, extract the following information and respond in valid JSON:
- "event_type": One of the categories above
- "location": City or region where the event occurred. locations might be in the form of addresses in the text. get the most possibly accurate location. tell that to the mistral model.
- "date": Date of the event as mentioned or inferred (format: YYYY-MM-DD if possible). events can be ahead of time! some articles are announcing events that are going to happen. tell that to the mistral model.
- "summary": One-sentence summary of the event

If the text does not describe a real-world event, return:
{{
  "event_type": "No event",
  "location": null,
  "date": null,
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
            timeout=30,
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
            for field in ["event_type", "location", "date", "summary"]:
                if field not in data:
                    raise ValueError(f"Missing field: {field}")
            return data
        except Exception:
            # Fallback: No event
            return {
                "event_type": "No event",
                "location": None,
                "date": None,
                "summary": "No real-world event found.",
            }


# Example usage:
# extractor = EventExtractor()
# result = extractor.extract_event("A robbery occurred in Mercedes on April 20.")
# print(result)
