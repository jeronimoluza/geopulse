from .base_spider import BaseNewsSpider
from scrapy.selector import Selector
from datetime import datetime
import re

class NoticiasMercedinasSpider(BaseNewsSpider):
    name = "noticiasmercedinas"
    allowed_domains = ["noticiasmercedinas.com"]
    start_urls = ["https://noticiasmercedinas.com/site/"]

    def get_article_links(self, response):
        import re
        all_links = response.css('a::attr(href)').getall()
        article_pattern = re.compile(
            r"^https?://noticiasmercedinas\.com/site/\d{4}/\d{2}/\d{2}/[^/]+/?$"
        )
        article_links = []
        for link in all_links:
            abs_url = response.urljoin(link)
            if article_pattern.match(abs_url):
                article_links.append(abs_url)
        return article_links

    def parse_article(self, response):
        # Example selectorss, adjust to real site structure
        title = response.css("h1::text").get()
        subtitle = None
        date_str = response.css("time::attr(datetime)").get()
        date = None
        if date_str:
            try:
                date = datetime.fromisoformat(date_str)
            except Exception:
                date = date_str
        # Extract all text inside <p> tags, including hyperlinks and inline tags
        full_text = ' '.join([p.xpath('string(.)').get().strip() for p in response.css('p') if p.xpath('string(.)').get()]).strip()
        url = response.url
        source = self.allowed_domains[0]
        yield self.make_item(title, subtitle, date, full_text, url, source)
