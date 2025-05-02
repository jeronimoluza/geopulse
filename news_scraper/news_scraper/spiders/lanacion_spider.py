from .base_spider import BaseNewsSpider
from scrapy.selector import Selector
from datetime import datetime
import re

class LaNacionSpider(BaseNewsSpider):
    name = "lanacion_spider"
    allowed_domains = ["lanacion.com.ar"]
    start_urls = ["https://www.lanacion.com.ar"]

    def get_article_links(self, response):
        all_links = response.css('a::attr(href)').getall()
        article_pattern = re.compile(r'^https://www\.lanacion\.com\.ar/[^/]+/.+-nid\d+/?$')

        article_links = []
        for link in all_links:
            abs_url = response.urljoin(link)
            if article_pattern.match(abs_url):
                article_links.append(abs_url)
        return article_links

    def parse_article(self, response):
        # Example selectorss, adjust to real site structure
        url = response.url
        title = response.css("h1::text").get()
        subtitle = response.css("h2::text").get()
        date_str = ", ".join(response.css("time::text").getall())
        # Extract the date string from the URL
        match = re.search(r'nid(\d{2})(\d{2})(\d{4})', url)
        if match:
            day, month, year = match.groups()
            date = datetime.strptime(f"{day}-{month}-{year}", "%d-%m-%Y")
        # Extract all text inside <p> tags, including hyperlinks and inline tags
        full_text = ' '.join([t.strip() for t in response.xpath("//section[@class='cuerpo__nota']//p//text()").getall()]).strip()
        source = self.allowed_domains[0]
        yield self.make_item(title, subtitle, date, full_text, url, source)
