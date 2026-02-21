import requests
from bs4 import BeautifulSoup

# TechCrunch RSS 피드 테스트
url = "https://techcrunch.com/feed/"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

r = requests.get(url, headers=headers, timeout=10)
soup = BeautifulSoup(r.content, 'html.parser')

# 첫 번째 아이템 확인
item = soup.find('item')
if item:
    print("=== 첫 번째 아이템 구조 ===")
    print(item.prettify()[:2000])
    
    print("\n=== Link 태그 상세 분석 ===")
    link_tag = item.find('link')
    if link_tag:
        print(f"Link tag: {link_tag}")
        print(f"Link tag name: {link_tag.name}")
        print(f"Link tag attrs: {link_tag.attrs}")
        print(f"Link tag text: '{link_tag.get_text(strip=True)}'")
        print(f"Link tag href: '{link_tag.get('href', '')}'")
