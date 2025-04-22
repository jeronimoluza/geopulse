import os
import json
from processing.extraction import EventExtractor

INPUT_DIR = os.path.join("news_scraper", "output")
OUTPUT_DIR = os.path.join("processing", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

EXTRACTOR = EventExtractor()


def process_file(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        articles = json.load(f)
    results = []
    for article in articles:
        text = article.get("full_text", "")
        event = EXTRACTOR.extract_event(text)
        event["source_url"] = article.get("url")
        event["source_title"] = article.get("title")
        results.append(event)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Processed {len(articles)} articles -> {output_path}")


def main():
    for fname in os.listdir(INPUT_DIR):
        if fname.endswith(".json"):
            input_path = os.path.join(INPUT_DIR, fname)
            output_fname = f"events_{fname}"
            output_path = os.path.join(OUTPUT_DIR, output_fname)
            process_file(input_path, output_path)


if __name__ == "__main__":
    main()
