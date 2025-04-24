import requests
import json
from typing import Dict, Any, Tuple

class PreFilter:
    """
    Pre-filters news articles using a lightweight Gemma-1B model to identify those likely to contain
    location-relevant events before passing them to the more expensive Mistral model.
    """

    def __init__(
        self, model_endpoint: str = "http://localhost:11434/api/generate"
    ):
        self.model_endpoint = model_endpoint

    def should_process(self, title: str, subtitle: str = "") -> Tuple[bool, str]:
        """
        Analyzes the title and subtitle to determine if the article likely contains
        a location-relevant event.
        
        Returns:
            Tuple[bool, str]: (should_process, reason)
            - should_process: True if the article should be processed by the main extractor
            - reason: Brief explanation of the decision
        """
        prompt = self._build_prompt(title, subtitle)
        try:
            response = self._query_model(prompt)
            decision = self._parse_response(response)
            return decision
        except Exception as e:
            print(f"Error in pre-filter: {e}")
            # On error, we'll process it to be safe
            return True, "Error in pre-filter, processing to be safe"

    def _build_prompt(self, title: str, subtitle: str = "") -> str:
        return f'''
You are a quick pre-filter that analyzes news titles and subtitles to determine if they are likely to contain information about real-world physical events with specific locations.

Consider an article relevant if it likely discusses:
- Ongoing or upcoming events (not past events)
- Events with physical locations
- Public gatherings, protests, or conflicts
- Natural disasters or weather events
- Infrastructure issues
- Public safety incidents
- Cultural or tourist events

Consider an article NOT relevant if it's about:
- Past events
- Policy announcements
- Business news without physical events
- Opinion pieces
- Obituaries
- General news without specific locations

Analyze this news article:
Title: {title}
{f"Subtitle: {subtitle}" if subtitle else ""}

Return a JSON with two fields:
- "should_process": boolean (true if the article likely contains a location-relevant event)
- "reason": brief explanation of your decision

Respond only with the JSON, nothing else.
'''

    def _query_model(self, prompt: str) -> str:
        payload = {"model": "gemma:1b", "prompt": prompt, "stream": False}
        headers = {"Content-Type": "application/json"}
        resp = requests.post(
            self.model_endpoint,
            data=json.dumps(payload),
            headers=headers,
            timeout=30,  # Shorter timeout for quick decisions
        )
        resp.raise_for_status()
        return resp.json().get("response", "")

    def _parse_response(self, response: str) -> Tuple[bool, str]:
        try:
            # Extract JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
            data = json.loads(json_str)
            
            # Validate fields
            if "should_process" not in data or "reason" not in data:
                raise ValueError("Missing required fields in response")
                
            return data["should_process"], data["reason"]
        except Exception as e:
            # On parsing error, we'll process it to be safe
            return True, f"Error parsing response: {str(e)}"
