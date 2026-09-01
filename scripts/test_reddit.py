import requests

url = "https://www.reddit.com/r/IndianFashionAddicts/comments/14r29cl.rss"

headers = {
    'User-Agent': 'python:myntra_research_bot:v1.0 (by /u/test)'
}

response = requests.get(url, headers=headers)
print("Status:", response.status_code)
if response.status_code == 200:
    print(f"Content length: {len(response.text)}")
    print(f"Sample: {response.text[:200]}")
    post = data[0]['data']['children'][0]['data']
    print(f"Title: {post['title']}")

    comments = data[1]['data']['children']
    print(f"Comments: {len(comments)}")
    if comments:
        print(f"First comment: {comments[0]['data'].get('body', '')[:100]}")
