from .base_spider import BaseNewsSpider
from scrapy.selector import Selector
from datetime import datetime
import re

class ClarinSpider(BaseNewsSpider):
    name = "clarin_spider"
    allowed_domains = ["clarin.com"]
    start_urls = ["https://www.clarin.com"]

    def get_article_links(self, response):
        all_links = response.css('a::attr(href)').getall()
        article_pattern = re.compile(r'^https://www\.clarin\.com/.*')
        article_links = []
        for link in all_links:
            abs_url = response.urljoin(link)
            if article_pattern.match(abs_url):
                article_links.append(abs_url)
        return article_links

    def parse_article(self, response):
        title = response.css("h1::text").get()
        date_str = response.xpath('/html/head/meta[@name="date"]//@content').get()
        date = response.xpath('/html/head/meta[@name="date"]//@content').get()
        subtitle = response.xpath('/html/head/meta[@name="description"]//@content').get()
        if date_str:
            try:
                date = datetime.fromisoformat(date_str)
            except Exception:
                date = date_str
        # Extract all text inside <p> tags, including hyperlinks and inline tags
        full_text = ' '.join([t.strip() for t in response.xpath("//div[@id='cuerpo']//p//text()").getall()
]).strip()
        url = response.url
        source = self.allowed_domains[0]
        yield self.make_item(title, subtitle, date, full_text, url, source)
