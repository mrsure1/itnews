"""
글로벌 AI 공식 채널의 채널 ID를 자동 검증합니다.
- @핸들 → externalId 추출
- RSS 200 OK 검증
- 출력: youtube_channels_global 딕셔너리 (collect_news.py 에 붙여넣기용)
"""
import re
import sys
import requests
import xml.etree.ElementTree as ET

CANDIDATES = {
    # === Tier 1: 글로벌 AI 공식 (사용자 OK: 영어 OK) ===
    "OpenAI": "@OpenAI",
    "Anthropic": "@anthropic-ai",
    "Google DeepMind": "@GoogleDeepMind",
    "Google for Developers": "@GoogleDevelopers",
    "NVIDIA": "@NVIDIA",
    "NVIDIA AI": "@NVIDIAAI",
    "NVIDIA Developer": "@NVIDIADeveloper",
    "Tesla": "@TeslaMotors",
    "AI at Meta": "@AIatMeta",
    "Microsoft": "@Microsoft",
    "Microsoft Developer": "@MicrosoftDeveloper",
    # === Tier 1: AI 툴/플랫폼 공식 ===
    "Cursor": "@cursor_ai",
    "ElevenLabs": "@elevenlabsio",
    "Suno": "@SunoAI_Official",
    "Runway": "@runwayml",
    "Hugging Face": "@HuggingFace",
    "Perplexity": "@perplexity_ai",
}

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_channel_id_from_handle(handle: str) -> str | None:
    """canonical link 또는 og:url을 통해 정확한 채널 ID를 추출."""
    url = f"https://www.youtube.com/{handle}"
    try:
        r = requests.get(url, headers=UA, timeout=10)
        if r.status_code != 200:
            return None
        # 1순위: canonical URL (페이지 자신의 채널 ID)
        m = re.search(r'<link rel="canonical" href="https?://www\.youtube\.com/channel/(UC[a-zA-Z0-9_\-]{22})"', r.text)
        if m:
            return m.group(1)
        # 2순위: og:url
        m = re.search(r'<meta property="og:url" content="https?://www\.youtube\.com/channel/(UC[a-zA-Z0-9_\-]{22})"', r.text)
        if m:
            return m.group(1)
        # 3순위: browseId (현재 페이지의 채널)
        m = re.search(r'"browseId":"(UC[a-zA-Z0-9_\-]{22})"', r.text)
        if m:
            return m.group(1)
        # 4순위: externalId
        m = re.search(r'"externalId":"(UC[a-zA-Z0-9_\-]{22})"', r.text)
        return m.group(1) if m else None
    except Exception:
        return None


def verify_rss(channel_id: str) -> tuple[bool, str]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "Feedfetcher-Google"})
        if r.status_code != 200:
            return False, f"status={r.status_code}"
        root = ET.fromstring(r.content)
        author = root.find('.//{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name')
        return True, author.text if author is not None else "?"
    except Exception as e:
        return False, str(e)


def main():
    print("=== 글로벌 AI 공식 채널 ID 자동 검증 ===\n")
    verified: dict[str, str] = {}
    failed: list[str] = []

    for name, handle in CANDIDATES.items():
        cid = get_channel_id_from_handle(handle)
        if not cid:
            print(f"  [FAIL]   {name:25s} {handle:30s} → 채널 ID 추출 실패")
            failed.append(name)
            continue
        ok, author = verify_rss(cid)
        status = "OK  " if ok else "FAIL"
        print(f"  [{status}] {name:25s} {handle:30s} → {cid}  ({author})")
        if ok:
            verified[author or name] = cid
        else:
            failed.append(name)

    print("\n=== 검증된 채널 (collect_news.py에 사용) ===\n")
    print("youtube_channels_global = {")
    for n, cid in verified.items():
        print(f'    "{n}": "{cid}",')
    print("}")

    if failed:
        print(f"\n[!] 검증 실패: {failed}")
    sys.exit(0 if verified else 1)


if __name__ == "__main__":
    main()
