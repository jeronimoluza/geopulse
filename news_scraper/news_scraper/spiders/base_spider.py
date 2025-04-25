import scrapy
from ..items import NewsScraperItem
from datetime import datetime
import unicodedata
import re
import json
import os
from pathlib import Path

class BaseNewsSpider(scrapy.Spider):
    """
    Base spider for news sites. Inherit from this and override:
      - name
      - start_urls
      - parse_article (to extract title, date, text, etc)
      - get_article_links (to extract article links from listing pages)
    """
    
    def __init__(self, *args, **kwargs):
        super(BaseNewsSpider, self).__init__(*args, **kwargs)
        # Load newspapers configuration
        self.country_code = self._get_country_code()
        # Create output directory if it doesn't exist
        output_dir = f"data/scraped/{self.country_code.lower()}"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
    def _get_country_code(self):
        """Determine country code from newspapers.json based on spider name"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                 'data', 'config', 'newspapers.json')
        try:
            with open(config_path, 'r') as f:
                newspapers_config = json.load(f)
                
            # Search for this spider in the configuration
            for country_code, country_data in newspapers_config.items():
                for newspaper in country_data.get('newspapers', []):
                    if newspaper.get('name') == self.name:
                        return country_code
            
            # If not found, return default
            self.logger.warning(f"Spider {self.name} not found in newspapers.json, using default country code")
            return "UNK"
        except Exception as e:
            self.logger.error(f"Error loading newspapers.json: {e}")
            return "UNK"
    
    custom_settings = {
        'FEED_FORMAT': 'json',
        'FEED_EXPORT_ENCODING': 'utf-8',
        'FEED_URI': 'data/scraped/%(country_code)s/%(name)s_%(time)s.json',
        'LOG_LEVEL': 'INFO',
    }

    def parse(self, response):
        # Extract article links from a listing page
        for url in self.get_article_links(response):
            yield response.follow(url, self.parse_article)

    def get_article_links(self, response):
        """Override this: Return a list of article URLs from a listing page."""
        raise NotImplementedError

    def parse_article(self, response):
        """Override this: Parse and yield a NewsScraperItem for a single article."""
        raise NotImplementedError

    def clean_text(self, text):
        """Remove unicode/control characters from a string."""
        if text is None:
            return None
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)
        return text.strip()

    def make_item(self, title, subtitle, date, full_text, url, source=None):
        return NewsScraperItem(
            title=self.clean_text(title),
            subtitle=self.clean_text(subtitle),
            date=date,
            full_text=self.clean_text(full_text),
            url=self.clean_text(url),
            source=self.clean_text(source or self.name),
            country_code=self.country_code
        )
