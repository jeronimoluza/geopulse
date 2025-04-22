import scrapy
from news_scraper.items import NewsScraperItem
from datetime import datetime

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

    def make_item(self, title, date, full_text, url, source=None):
        return NewsScraperItem(
            title=title,
            date=date,
            full_text=full_text,
            url=url,
            source=source or self.name
        )
