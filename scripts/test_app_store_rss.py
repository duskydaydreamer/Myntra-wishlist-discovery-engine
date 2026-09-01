import requests
import json
import time
from datetime import datetime

app_id = 907394059
country = 'in'

def fetch_rss_reviews(app_id, country='in', pages=10):
    all_reviews = []
    
    for page in range(1, pages + 1):
        url = f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"Failed to fetch page {page}: {response.status_code}")
            break
            
        try:
            data = response.json()
            entries = data.get('feed', {}).get('entry', [])
            
            # The first entry is sometimes metadata about the app itself, skip it if 'author' is not a review author
            if entries and 'im:name' in entries[0]:
                entries = entries[1:]
                
            if not entries:
                break
                
            for entry in entries:
                review = {
                    'id': entry.get('id', {}).get('label'),
                    'title': entry.get('title', {}).get('label'),
                    'review': entry.get('content', {}).get('label'),
                    'rating': int(entry.get('im:rating', {}).get('label', 0)),
                    'date': entry.get('updated', {}).get('label'), # e.g. "2023-01-01T12:00:00-07:00"
                    'userName': entry.get('author', {}).get('name', {}).get('label')
                }
                all_reviews.append(review)
                
            time.sleep(1) # Be nice to the API
        except Exception as e:
            print(f"Error parsing page {page}: {e}")
            break
            
    return all_reviews

if __name__ == "__main__":
    reviews = fetch_rss_reviews(app_id, country)
    print(f"Fetched {len(reviews)} reviews from RSS feed.")
    if reviews:
        print("Sample:", json.dumps(reviews[0], indent=2))
