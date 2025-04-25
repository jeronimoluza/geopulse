import scrapy
from ..items import NewsScraperItem
from datetime import datetime
import unicodedata
import re

class BaseNewsSpider(scrapy.Spider):
    """
    Base spider for news sites. Inherit from this and override:
      - name
      - start_urls
      - parse_article (to extract title, date, text, etc)
      - get_article_links (to extract article links from listing pages)
    """
    custom_settings = {
        'FEED_FORMAT': 'json',
        'FEED_EXPORT_ENCODING': 'utf-8',
        'FEED_URI': 'output/%(name)s_%(time)s.json',
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
            source=self.clean_text(source or self.name)
        )
