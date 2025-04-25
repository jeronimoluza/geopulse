from typing import List, Dict
import json
import requests
from datetime import datetime
from pathlib import Path
from .utils import chunk_text
from tqdm import tqdm

class NewsSummarizer:
    def __init__(self, model_endpoint: str = "http://localhost:11434/api/generate"):
        self.model_endpoint = model_endpoint

    def _generate_summary(self, text: str) -> str:
        prompt = f"Summarize the following news article in a concise way:\n\n{text}\n\nSummary:"
        
        payload = {
            # "model": "qwen2:0.5b",
            "model": "mistral",
            # "model": "tinyllama",
            "prompt": prompt,
            "stream": False
        }
        headers = {"Content-Type": "application/json"}
        
        try:
            resp = requests.post(
                self.model_endpoint,
                data=json.dumps(payload),
                headers=headers,
                timeout=60
            )
            resp.raise_for_status()
            summary = resp.json().get("response", "")
            
            # Extract only the generated summary after the prompt
            if "Summary:" in summary:
                return summary.split("Summary:")[1].strip()
            return summary.strip()
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return ""

    def summarize_chunks(self, chunks: List[str]) -> str:
        """Summarize each chunk and combine them."""
        chunk_summaries = [self._generate_summary(chunk) for chunk in chunks]
        combined_text = " ".join(chunk_summaries)
        return self._generate_summary(combined_text)

    def process_country_articles(self, country_code: str, articles: List[Dict]) -> Dict:
        """Process all articles for a country and generate summaries."""
        processed_articles = []
        all_summaries = []

        for article in tqdm(articles):
            if article.get("full_text") == '':
                continue
            # Chunk the full text if it exists
            chunks = chunk_text(article.get('full_text', ''))
            
            # Generate article summary
            article_summary = self.summarize_chunks(chunks)
            
            processed_article = {
                'title': article['title'],
                'summary': article_summary,
                'url': article['url']
            }
            processed_articles.append(processed_article)
            all_summaries.append(article_summary)

        # Generate country-level summary
        country_summary = self._generate_summary("\n".join(all_summaries))

        return {
            'country': country_code,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'articles': processed_articles,
            'country_summary': country_summary
        }

    def save_country_summary(self, summary: Dict, output_dir: str):
        """Save the country summary to a JSON file."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"{summary['country']}_{summary['date']}.json"
        with open(output_path / filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
