from typing import List, Dict, Tuple, Any
import json
import requests
from datetime import datetime
from pathlib import Path
import os
from .utils import chunk_text
from tqdm import tqdm

class NewsSummarizer:
    def __init__(self, model_endpoint: str = "http://localhost:11434/api/generate"):
        self.model_endpoint = model_endpoint

    def _generate_summary(self, text: str, prompt_template: str = None) -> str:
        """Generate a summary using the Mistral model"""
        if prompt_template is None:
            prompt = f"Summarize the following news article in a concise way:\n\n{text}\n\nSummary:"
        else:
            prompt = prompt_template.format(text=text)
        
        payload = {
            "model": "mistral",
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
            if "Summary:" in summary and prompt_template is None:
                return summary.split("Summary:")[1].strip()
            return summary.strip()
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return ""
            
    def _extract_topics_articles(self, articles_info: List[Dict]) -> Tuple[List[str], List[str]]:
        """Extract the 2 most mentioned topics and return IDs of articles for those topics"""
        # Format the articles info for the prompt
        article_texts = []
        for article in articles_info:
            article_id = article.get('article_id', '')
            title = article.get('title', '')
            subtitle = article.get('subtitle', '') or ''
            article_texts.append(f"ID: {article_id}\nTitle: {title}\nSubtitle: {subtitle}")
        
        combined_text = "\n\n".join(article_texts)
        
        prompt_template = (
            "Below are IDs, titles and subtitles from recent news articles in a specific country.\n\n"
            "{text}\n\n"
            "Based on these titles and subtitles, identify the 2 main topics or themes being discussed "
            "in the news. For each topic, select the article ID that best represents that topic.\n\n"
            "Format your response exactly as follows:\n"
            "Topic 1: [topic description]\nArticle ID 1: [article_id]\n"
            "Topic 2: [topic description]\nArticle ID 2: [article_id]"
        )
        
        response = self._generate_summary(combined_text, prompt_template)
        
        # Extract topics and article IDs from the response
        topics = []
        article_ids = []
        
        lines = response.split('\n')
        for i, line in enumerate(lines):
            if line.startswith("Topic ") and ":" in line:
                topic_desc = line.split(":", 1)[1].strip()
                topics.append(topic_desc)
            elif line.startswith("Article ID ") and ":" in line:
                article_id = line.split(":", 1)[1].strip()
                article_ids.append(article_id)
        
        # Ensure we have exactly 2 topics and article IDs
        while len(topics) < 2:
            topics.append(f"Miscellaneous topic {len(topics)+1}")
        
        # If we don't have enough article IDs, use the first ones from the input
        while len(article_ids) < 2 and len(articles_info) > 0:
            missing_ids = 2 - len(article_ids)
            for i in range(min(missing_ids, len(articles_info))):
                if articles_info[i]['article_id'] not in article_ids:
                    article_ids.append(articles_info[i]['article_id'])
        
        return topics[:2], article_ids[:2]

    def summarize_chunks(self, chunks: List[str]) -> str:
        """Summarize each chunk and combine them."""
        chunk_summaries = [self._generate_summary(chunk) for chunk in chunks]
        combined_text = " ".join(chunk_summaries)
        return self._generate_summary(combined_text)
        
    def summarize_article_for_topic(self, article: Dict, topic: str) -> str:
        """Generate a concise summary sentence for an article related to a specific topic"""
        full_text = article.get('full_text', '')
        if not full_text:
            return f"No information available about {topic}."
            
        # Chunk the text if it's long
        chunks = chunk_text(full_text)
        
        # If we have multiple chunks, summarize each and then combine
        if len(chunks) > 1:
            # First get a combined summary of all chunks
            article_summary = self.summarize_chunks(chunks)
        else:
            article_summary = full_text
            
        # Now generate a topic-focused summary
        prompt_template = (
            "Below is a news article about '{topic}':\n\n"
            "{text}\n\n"
            "Provide a single concise sentence that summarizes the key information about '{topic}' from this article."
        )
        
        prompt = prompt_template.format(topic=topic, text=article_summary)
        return self._generate_summary(article_summary, prompt)

    def process_country_articles(self, country_code: str, articles_metadata: List[Dict], full_articles: List[Dict] = None) -> Dict:
        """Process articles for a country, extract topics, and generate summaries.
        
        Args:
            country_code: The country code (e.g., 'ARG')
            articles_metadata: List of dicts with article_id, title, subtitle
            full_articles: Optional list of full article data with article_id and full_text
            
        Returns:
            Dict with country code, date, topics and summaries
        """
        if not articles_metadata:
            return {
                'country': country_code,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'summary': "No articles available for this country."
            }
            
        # Extract the 2 most mentioned topics and get representative article IDs
        topics, article_ids = self._extract_topics_articles(articles_metadata)
        
        # If we have full articles data, find the articles by ID
        topic_summaries = []
        if full_articles:
            # Create a lookup dictionary for quick access to full articles by ID
            articles_by_id = {article.get('article_id', ''): article for article in full_articles}
            
            # Generate a summary for each topic using the corresponding article
            for i, (topic, article_id) in enumerate(zip(topics, article_ids)):
                article = articles_by_id.get(article_id)
                if article:
                    summary = self.summarize_article_for_topic(article, topic)
                    topic_summaries.append(summary)
                else:
                    # If we can't find the article, use a placeholder
                    topic_summaries.append(f"No detailed information available about {topic}.")
        else:
            # If we don't have full articles, use placeholders
            topic_summaries = [f"No detailed information available about {topic}." for topic in topics]
            
        # Combine the summaries into a single string
        combined_summary = ". ".join(topic_summaries)
        
        return {
            'country': country_code,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'topics': topics,
            'article_ids': article_ids,
            'summary': combined_summary
        }

    def save_country_summary(self, summary: Dict, output_dir: str):
        """Save the country summary to a JSON file."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"{summary['country']}_{summary['date']}.json"
        with open(output_path / filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
            
    def save_country_summaries_json(self, summaries: Dict[str, str], output_dir: str = "data/summary"):
        """Save all country summaries to a single JSON file.
        
        Args:
            summaries: Dictionary mapping country codes to summary strings
            output_dir: Directory to save the JSON file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        output_file = output_path / "country_summaries.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summaries, f, ensure_ascii=False, indent=2)
