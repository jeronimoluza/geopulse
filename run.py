import os
import sys
import json
import argparse

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

from processing.pipeline import NewsPipeline
from processing.summarizer import NewsSummarizer

INPUT_DIR = os.path.join("news_scraper", "output")
OUTPUT_DIR = os.path.join("processing", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SUMMARIZER = NewsSummarizer()


def process_file(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    # Get country code from filename (e.g., ARG_20250425.json -> ARG)
    country_code = os.path.basename(input_path).split('_')[0]
    
    # Process articles and generate summaries
    country_summary = SUMMARIZER.process_country_articles(country_code, articles)
    
    # Save the processed output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(country_summary, f, ensure_ascii=False, indent=2)
    print(f"Processed {len(articles)} articles for {country_code} -> {output_path}")


def run_scraper():
    """Run the news scraping and summarization pipeline"""
    config_path = os.path.join("data", "config", "newspapers.json")
    pipeline = NewsPipeline(config_path, OUTPUT_DIR)
    pipeline.run_spiders()

def run_summarizer():
    """Run the summarization on scraped articles"""
    config_path = os.path.join("data", "config", "newspapers.json")
    pipeline = NewsPipeline(config_path, OUTPUT_DIR)
    pipeline.process_country_summaries()

def main():
    parser = argparse.ArgumentParser(description="GeoPulse News Pipeline")
    parser.add_argument(
        "action",
        choices=["scrape", "summarize", "all"],
        help="Action to perform: scrape news, generate summaries, or both"
    )
    
    args = parser.parse_args()
    
    if args.action in ["scrape", "all"]:
        print("Running news scraping pipeline...")
        run_scraper()
    
    if args.action in ["summarize", "all"]:
        print("Running news summarization...")
        run_summarizer()


if __name__ == "__main__":
    main()
