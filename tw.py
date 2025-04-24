import tweepy


client = tweepy.Client(
    bearer_token=bearer_token,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret_key,
    access_token=access_token,
    access_token_secret=access_token_secret,
)

query = "(protest OR incendio OR tormenta) lang:es -is:retweet"

tweets = client.search_recent_tweets(query=query, max_results=10)

for tweet in tweets.data:
    print(tweet.text)
    # Send to Mistral for extraction
