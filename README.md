# geopulse

This project builds a real-time system that extracts, geotags, and visualizes real-world events from news articles. Events include conflict, climate, health, infrastructure, crime, and cultural updates. The final output is a structured JSON feed that can be displayed on a map-based dashboard.

📦 Current Component: News Scraping
This module handles the hourly ingestion of news articles from various online sources using Scrapy. It is designed with scalability and modularity in mind—each news site has its own spider class, making it easy to add new sources.
