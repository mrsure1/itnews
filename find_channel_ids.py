import requests
import re

def search_channel(search_term):
    """유튜브 검색으로 채널 ID 찾기"""
    url = f"https://www.youtube.com/results?search_query={requests.utils.quote(search_term)}&sp=EgIQAg%3D%3D"  # 채널 탭
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9"
    }
    r = requests.get(url, headers=headers, timeout=10)
    # UC로 시작하는 채널 ID들 추출
    ids = re.findall(r'"channelId":"(UC[a-zA-Z0-9_\-]{22})"', r.text)
    unique_ids = list(dict.fromkeys(ids))
    return unique_ids[:5]

print("=== 코딩알려주는누나 채널 검색 ===")
ids = search_channel("코딩알려주는누나")
for cid in ids:
    yt_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
    r = requests.get(yt_url, timeout=5, headers={"User-Agent": "Feedfetcher-Google"})
    if r.status_code == 200:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.content)
        ns = {'yt': 'http://www.youtube.com/xml/schemas/2015'}
        author = root.find('.//{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name')
        name = author.text if author is not None else "?"
        print(f"  OK | 채널명: {name} | ID: {cid}")
    else:
        print(f"  FAIL | ID: {cid}")
