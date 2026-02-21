import requests
import json
import os

def check_url(url, description):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0 4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"[{response.status_code}] {description}: {url}")
        return response.status_code == 200
    except Exception as e:
        print(f"[ERR] {description}: {e}")
        return False

print("--- RSS/API URL Availability Check ---")
check_url('https://hacker-news.firebaseio.com/v0/topstories.json', 'Hacker News API')
check_url('https://openai.com/news/rss.xml', 'OpenAI Blog RSS (Variant 1)')
check_url('https://openai.com/index.xml', 'OpenAI Blog RSS (Variant 2)')
check_url('https://deepmind.google/blog/rss.xml', 'Google DeepMind Blog')
check_url('https://research.google/blog/rss', 'Google Research Blog')
check_url('https://www.microsoft.com/en-us/research/feed/', 'Microsoft Research Blog')

print("\n--- JSON Data File Check ---")
json_path = 'news_data.json'
if os.path.exists(json_path):
    try:
        with open(json_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
            print(f"news_data.json is valid. Contains {len(data)} items.")
    except json.JSONDecodeError:
        print("news_data.json is CORRUPTED (JSONDecodeError).")
    except Exception as e:
        print(f"Error reading news_data.json: {e}")
else:
    print("news_data.json does not exist.")
