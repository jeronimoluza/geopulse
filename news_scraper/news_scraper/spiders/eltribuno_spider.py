from .base_spider import BaseNewsSpider
from scrapy.selector import Selector
from datetime import datetime
import re

class ElTribunoSpider(BaseNewsSpider):
    name = "eltribuno"
    allowed_domains = ["eltribuno.com"]
    start_urls = ["https://eltribuno.com/"]

    def get_article_links(self, response):
        all_links = response.css('a::attr(href)').getall()
        article_pattern = re.compile(r'^https://www\.eltribuno\.com/[^/]+/\d{4}-\d{1,2}-\d{1,2}-.*')
        article_links = []
        for link in all_links:
            abs_url = response.urljoin(link)
            if article_pattern.match(abs_url):
                article_links.append(abs_url)
        return article_links

    def parse_article(self, response):
        # Example selectorss, adjust to real site structure
        title = response.css("h1::text").get()
        date_str = response.css("input::attr(data-fecha_c)").get()
        date = None
        subtitle = response.css('div.articulo__intro::text').get()
        if date_str:
            try:
                date = datetime.fromisoformat(date_str)
            except Exception:
                date = date_str
        # Extract all text inside <p> tags, including hyperlinks and inline tags
        full_text = ' '.join([t.strip() for t in response.css('div[amp-access="mostrarNota"] p::text').getall()
]).strip()
        url = response.url
        source = self.allowed_domains[0]
        yield self.make_item(title, subtitle, date, full_text, url, source)
