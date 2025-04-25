import json
from pathlib import Path
from typing import Dict, List
import logging
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from .summarizer import NewsSummarizer
from news_scraper.news_scraper.spiders.clarin_spider import ClarinSpider
from news_scraper.news_scraper.spiders.lanacion_spider import LaNacionSpider
from news_scraper.news_scraper.spiders.lpo_spider import LPOSpider

SPIDER_MAP = {
    'clarin_spider': ClarinSpider,
    'lanacion_spider': LaNacionSpider,
    'lpo_spider': LPOSpider
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsPipeline:
    def __init__(self, config_path: str, output_dir: str):
        self.config_path = Path(config_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.summarizer = NewsSummarizer()
        
        # Load newspaper configuration
        with open(self.config_path) as f:
            self.config = json.load(f)

    def _load_spiders(self) -> Dict[str, List[str]]:
        """Load all available spiders and group them by country."""
        country_spiders = {}
        spider_files = Path("news_scraper/news_scraper/spiders").glob("*.py")
        
        for spider_file in spider_files:
            if spider_file.stem not in ['__init__', 'base_spider']:
                country_code = self._get_country_code(spider_file.stem)
                if country_code:
                    if country_code not in country_spiders:
                        country_spiders[country_code] = []
                    country_spiders[country_code].append(spider_file.stem)
        
        return country_spiders

    def _get_country_code(self, spider_name: str) -> str:
        """Get country code for a spider based on config."""
        for country_code, country_data in self.config.items():
            for newspaper in country_data['newspapers']:
                if newspaper['name'] == spider_name:
                    return country_code
        return None

    def run_spiders(self):
        """Run all spiders to collect articles."""
        country_spiders = self._load_spiders()
        process = CrawlerProcess(get_project_settings())
        
        for country_code, spiders in country_spiders.items():
            logger.info(f"Processing country: {country_code}")
            
            # Run spiders for this country
            for spider_name in spiders:
                if spider_name in SPIDER_MAP:
                    process.crawl(SPIDER_MAP[spider_name])
        
        # Wait for all spiders to finish
        process.start()

    def process_country_summaries(self):
        """Process all spider outputs and generate summaries for each country."""
        country_articles = {}
        today = datetime.now().strftime('%Y-%m-%d')
        spider_outputs = Path("output").glob(f"*_{today}*.json")
        
        # First collect all articles by country
        for output_file in spider_outputs:
            with open(output_file) as f:
                spider_articles = json.load(f)
                if spider_articles:
                    # Get country code from spider name
                    spider_name = output_file.stem.split('_')[0]
                    country_code = self._get_country_code(spider_name)
                    if country_code:
                        if country_code not in country_articles:
                            country_articles[country_code] = []
                        country_articles[country_code].extend(spider_articles)
        
        # Then process summaries for each country
        for country_code, articles in country_articles.items():
            if not articles:
                logger.warning(f"No articles found for country {country_code}")
                continue
                
            logger.info(f"Generating summaries for {country_code} ({len(articles)} articles)")
            country_summary = self.summarizer.process_country_articles(country_code, articles)
            
            # Save the processed output
            self.summarizer.save_country_summary(
                country_summary,
                self.output_dir / "processed"
            )
