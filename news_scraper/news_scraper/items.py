# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class NewsScraperItem(scrapy.Item):
    title = scrapy.Field()
    date = scrapy.Field()
    full_text = scrapy.Field()
    url = scrapy.Field()
    source = scrapy.Field()
