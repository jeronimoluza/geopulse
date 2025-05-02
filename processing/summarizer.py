from typing import List, Dict, Tuple, Any, Counter as CounterType
import json
import requests
from datetime import datetime
from pathlib import Path
import os
import random
from collections import Counter, defaultdict
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
            "model": "tinyllama",
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
            
    def _extract_topic_articles_chunked(self, articles_info: List[Dict], topics: List[str], chunk_size: int = 15) -> Dict[str, Dict[str, int]]:
        """Categorize articles into predefined topics using a chunking strategy to handle token limits
        
        Args:
            articles_info: List of article metadata (article_id, title, subtitle)
            topics: List of predefined topics to categorize articles into
            chunk_size: Number of articles to process in each chunk
            
        Returns:
            Dictionary mapping topics to news themes and their occurrence counts
        """
        # Shuffle articles to randomize the order
        shuffled_articles = articles_info.copy()
        random.shuffle(shuffled_articles)
        
        # Initialize topic news counters
        topic_news_counters = {topic: Counter() for topic in topics}
        
        # Process articles in chunks
        batches = list(range(0, len(shuffled_articles), chunk_size))
        for i in tqdm(batches):
            chunk = shuffled_articles[i:i+chunk_size]
            chunk_results = self._process_article_chunk(chunk, topics, i//chunk_size, topic_news_counters)
            
            # Update the counters with results from this chunk
            for topic, news_counter in chunk_results.items():
                topic_news_counters[topic].update(news_counter)
        
        # Convert counters to a more structured format
        topic_news = {}
        for topic, counter in topic_news_counters.items():
            if counter:
                # Get the news with the highest count for each topic
                most_common_news = counter.most_common(1)
                if most_common_news:
                    news_text, count = most_common_news[0]
                    topic_news[topic] = {
                        'news': news_text,
                        'count': count
                    }
        
        return topic_news
    
    def _process_article_chunk(self, articles_chunk: List[Dict], topics: List[str], 
                               chunk_index: int, previous_results: Dict[str, CounterType]) -> Dict[str, CounterType]:
        """Process a chunk of articles and extract topic information
        
        Args:
            articles_chunk: A subset of article metadata
            topics: List of predefined topics
            chunk_index: Index of the current chunk
            previous_results: Results from previous chunks
            
        Returns:
            Updated topic news counters
        """
        # Format the articles info for the prompt
        article_texts = []
        for i, article in enumerate(articles_chunk):
            article_id = article.get('article_id', '')
            title = article.get('title', '')
            subtitle = article.get('subtitle', '') or ''
            article_texts.append(f"Article {i+1}:\nID: {article_id}\nTitle: {title}\nSubtitle: {subtitle}")
        
        combined_text = "\n\n".join(article_texts)
        topics_list = ", ".join(topics)
        
        # Construct the prompt based on whether this is the first chunk or not
        if chunk_index == 0:
            # First chunk - identify main news for each topic
            prompt_template = (
                "Below are titles and subtitles from recent news articles in a specific country.\n\n"
                "{text}\n\n"
                f"Categorize these articles into the following topics: {topics_list}.\n"
                "For each topic, identify what's the main news being discussed and how many articles refer to it.\n\n"
                "Format your response exactly as follows:\n"
                "Topic: [topic name]\nMain news: [brief description of the main news]\nArticle count: [number of articles]\n\n"
                "Topic: [topic name]\nMain news: [brief description of the main news]\nArticle count: [number of articles]\n\n"
                "And so on for each topic that has relevant articles."
            )
        else:
            # Subsequent chunks - update with previous results
            context = "\n\n"
            for topic, counter in previous_results.items():
                if counter:
                    most_common = counter.most_common(1)
                    if most_common:
                        news, count = most_common[0]
                        context += f"Topic: {topic}\nCurrent main news: {news}\nCurrent count: {count}\n\n"
            
            prompt_template = (
                "Below are additional titles and subtitles from news articles.\n\n"
                "{text}\n\n"
                "Based on previous analysis, these are the current main news topics and their counts:\n"
                f"{context}\n"
                f"Analyze these new articles and update the main news for each topic: {topics_list}.\n"
                "If you find articles about the same main news, increase the count.\n"
                "If you find a new main news that appears more frequently in this batch, update it.\n\n"
                "Format your response exactly as follows:\n"
                "Topic: [topic name]\nMain news: [brief description of the main news]\nArticle count: [number of articles]\n\n"
            )
        
        response = self._generate_summary(combined_text, prompt_template)
        
        # Parse the response to extract topics and news
        chunk_results = {topic: Counter() for topic in topics}
        
        current_topic = None
        current_news = None
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("Topic:") and ":" in line:
                topic_name = line.split(":", 1)[1].strip().lower()
                current_topic = self._find_closest_topic(topic_name, topics)
                current_news = None
            elif line.startswith("Main news:") and ":" in line and current_topic:
                current_news = line.split(":", 1)[1].strip()
            elif line.startswith("Article count:") and ":" in line and current_topic and current_news:
                try:
                    count_text = line.split(":", 1)[1].strip()
                    count = int(count_text)
                    chunk_results[current_topic][current_news] += count
                except ValueError:
                    # If count can't be parsed, assume 1
                    chunk_results[current_topic][current_news] += 1
        
        return chunk_results
        
    def _find_closest_topic(self, topic_name: str, predefined_topics: List[str]) -> str:
        """Find the closest matching predefined topic for a given topic name"""
        topic_name = topic_name.lower()
        
        # Direct match
        for topic in predefined_topics:
            if topic.lower() == topic_name:
                return topic
                
        # Partial match
        for topic in predefined_topics:
            if topic.lower() in topic_name or topic_name in topic.lower():
                return topic
                
        # Default to miscellaneous if available, otherwise first topic
        if 'miscellaneous' in predefined_topics:
            return 'miscellaneous'
        return predefined_topics[0]

    def summarize_chunks(self, chunks: List[str]) -> str:
        """Summarize each chunk and combine them."""
        chunk_summaries = [self._generate_summary(chunk) for chunk in chunks]
        combined_text = " ".join(chunk_summaries)
        return self._generate_summary(combined_text)
        
    def _generate_news_summary(self, articles: List[Dict], news_theme: str) -> str:
        """Generate a concise summary sentence for articles related to a specific news theme
        
        Args:
            articles: List of full article data
            news_theme: The main news theme to summarize
            
        Returns:
            A concise summary sentence (max 15 words)
        """
        if not articles:
            return f"No information available about {news_theme}."
            
        # Extract full texts
        full_texts = []
        for article in articles:
            full_text = article.get('full_text', '')
            if full_text:
                full_texts.append(full_text)
        
        if not full_texts:
            return f"No detailed information available about {news_theme}."
            
        # Combine texts (limit to avoid token limits)
        combined_text = "\n\n".join(full_texts[:3])  # Limit to 3 articles
        
        # Generate a concise summary (max 15 words)
        prompt_template = (
            "Below are news articles about '{topic}':\n\n"
            "{text}\n\n"
            "Provide a SINGLE CONCISE SENTENCE (maximum 15 words) that summarizes "
            "the key information about '{topic}' from these articles."
        )
        
        prompt = prompt_template.format(topic=news_theme, text=combined_text)
        summary = self._generate_summary(combined_text, prompt)
        
        return summary

    def process_country_articles(self, country_code: str, articles_metadata: List[Dict], full_articles: List[Dict] = None, 
                               predefined_topics: List[str] = None) -> Dict:
        """Process articles for a country, extract topics, and generate summaries.
        
        Args:
            country_code: The country code (e.g., 'ARG')
            articles_metadata: List of dicts with article_id, title, subtitle
            full_articles: Optional list of full article data with article_id and full_text
            predefined_topics: List of topics to categorize articles into
            
        Returns:
            Dict with country code, date, topics and summaries
        """
        if not articles_metadata:
            return {
                'country': country_code,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'summary': "No articles available for this country."
            }
            
        # Use the chunking strategy to categorize articles and identify main news for each topic
        topic_news = self._extract_topic_articles_chunked(articles_metadata, predefined_topics)
        
        # Create a lookup dictionary for quick access to full articles by ID
        articles_by_id = {}
        if full_articles:
            articles_by_id = {article.get('article_id', ''): article for article in full_articles}
            
        # Generate summaries for each topic based on the main news identified
        topic_summaries = {}
        
        for topic, news_data in topic_news.items():
            news_text = news_data.get('news', '')
            count = news_data.get('count', 0)
            
            if news_text and count > 0:
                # Find articles related to this main news
                related_articles = []
                for article in full_articles:
                    title = article.get('title', '')
                    subtitle = article.get('subtitle', '')
                    combined = f"{title} {subtitle}".lower()
                    
                    # Simple relevance check - if the news text appears in the title or subtitle
                    # This could be improved with more sophisticated matching
                    if any(keyword in combined for keyword in news_text.lower().split()):
                        related_articles.append(article)
                
                # Limit to a few articles for summarization
                related_articles = related_articles[:3]
                
                if related_articles:
                    # Generate a concise summary based on the full text of related articles
                    summary = self._generate_news_summary(related_articles, news_text)
                    
                    # Get the sources (newspaper names) for these articles
                    sources = []
                    article_ids = []
                    for article in related_articles:
                        article_id = article.get('article_id')
                        if article_id:
                            article_ids.append(article_id)
                        
                        source = article.get('source')
                        if source and source not in sources:
                            sources.append(source)
                    
                    topic_summaries[topic] = summary
        
        return {
            'country': country_code,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'topics': topic_summaries
        }

    def save_country_summary(self, summary: Dict, output_dir: str):
        """Save the country summary to a JSON file."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"{summary['country']}_{summary['date']}.json"
        with open(output_path / filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
            
    def save_country_summaries_json(self, country_summaries: Dict[str, Dict], output_dir: str = "data/summary"):
        """Save all country summaries to a single JSON file in the required format.
        
        Args:
            country_summaries: Dictionary mapping country codes to summary dictionaries
            output_dir: Directory to save the JSON file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        output_file = output_path / "country_summaries.json"
        
        # Format the output according to requirements
        formatted_output = {
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        # Add each country's topic summaries
        for country_code, country_data in country_summaries.items():
            formatted_output[country_code] = {}
            
            # Extract topic summaries from the country data
            topics_data = country_data.get('topics', {})
            
            for topic, topic_data in topics_data.items():
                # Format as "topic: summary sentence"
                summary = topic_data.get('summary', '')
                formatted_output[country_code][topic] = f"{summary}"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(formatted_output, f, ensure_ascii=False, indent=2)
