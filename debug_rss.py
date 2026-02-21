import requests
from bs4 import BeautifulSoup

def clean_summary(text):
    return text

def sanitize_url(url):
    return url

def extract_image_from_rss_item(item_soup, description_html: str) -> str:
    print(f"--- Debug Image Extraction ---")
    media_content = item_soup.find("media:content")
    if media_content:
        print(f"Found media:content: {media_content.get('url')}")
    
    media_thumbnail = item_soup.find("media:thumbnail")
    if media_thumbnail:
         print(f"Found media:thumbnail: {media_thumbnail.get('url')}")

    enclosure = item_soup.find("enclosure")
    if enclosure:
         print(f"Found enclosure: {enclosure.get('url')}")

    if description_html:
        desc_soup = BeautifulSoup(description_html, "html.parser")
        image_tag = desc_soup.find("img")
        if image_tag:
             print(f"Found img in description: {image_tag.get('src')}")

    # Check content:encoded
    content_encoded = item_soup.find("content:encoded") or item_soup.find("content")
    if content_encoded:
        print(f"Found content:encoded tag")
        content_soup = BeautifulSoup(content_encoded.get_text(), "html.parser")
        img = content_soup.find("img")
        if img:
            print(f"Found img in content:encoded: {img.get('src')}")

    return ""

def test_feed(url):
    print(f"Testing {url}...")
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    try:
        soup = BeautifulSoup(r.content, "xml")
    except Exception as e:
        print(f"XML parser failed: {e}")
        soup = BeautifulSoup(r.content, "html.parser")
    
    if not soup.find("item"):
         soup = BeautifulSoup(r.content, "html.parser")
    
    items = soup.find_all("item")[:1]
    for item in items:
        # Print raw item content to see what's really there
        print(f"--- Raw Item Content (first 1000 chars) ---")
        print(str(item)[:1000])
        
        title_tag = item.find("title")
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        print(f"Item: {title}")
        
        # Print all children tags to see what we have
        print("  Tags found in item:")
        for child in item.find_all(recursive=False):
            if child.name:
                print(f"    - {child.name} (attrs: {child.attrs})")

        desc = item.find("description")
        desc_html = desc.decode_contents() if desc else ""
        extract_image_from_rss_item(item, desc_html)

if __name__ == "__main__":
    test_feed("https://techcrunch.com/feed/")
