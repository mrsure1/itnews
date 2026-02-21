import requests
from bs4 import BeautifulSoup

url = "https://news.naver.com/section/105"  # IT/과학 섹션

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

print(f"Fetching: {url}")
r = requests.get(url, headers=headers, timeout=5)
print(f"Status: {r.status_code}")

soup = BeautifulSoup(r.text, "html.parser")

# 뉴스 리스트 찾기
news_items = soup.select(".sa_text, .cjs_news_tw, .list_body li")
print(f"\nFound {len(news_items)} potential news items")

if news_items:
    print("\n=== First 3 items structure ===")
    for i, item in enumerate(news_items[:3]):
        print(f"\n--- Item {i+1} ---")
        # 제목 찾기
        title_elem = item.select_one("strong.sa_text_strong, .sa_text_title, a.sa_text_lede")
        if title_elem:
            print(f"Title: {title_elem.get_text(strip=True)[:50]}")
        
        # 링크 찾기
        link_elem = item.select_one("a[href]")
        if link_elem:
            print(f"Link: {link_elem.get('href')[:80]}")
        
        # 이미지 찾기
        img_elem = item.select_one("img")
        if img_elem:
            print(f"Image: {img_elem.get('src', img_elem.get('data-src', 'N/A'))[:80]}")
        
        # HTML 구조 확인
        print(f"Classes: {item.get('class')}")
else:
    print("\n=== Trying alternative selectors ===")
    # 다른 선택자 시도
    alternatives = [
        ".section_article",
        "article",
        ".news_area",
        "ul.sa_list li"
    ]
    for selector in alternatives:
        items = soup.select(selector)
        if items:
            print(f"Found {len(items)} items with selector: {selector}")
            if items:
                print(f"  First item classes: {items[0].get('class')}")
