import requests

channels = {
    "조코딩": "UC7iE58h95d2uO2K1gXGf02A",
    "테크몽": "UCi0yM44hF1YJ65Xz5Zl5X-Q",
    "빵형의 개발도상국": "UC6s7g0kE4-2-l4_Q1f-Q9fA",
    "일잘러 장피엠": "UCz93u97R7u-r_9G7Jg98p4A",
    "게으른 일잘러": "UCoa3QhN0V9hS8_2oD5g8pLw",
    "초인쌤": "UCh2U1Uq1N_18N3jO5q7v-wQ",
    "AI 코리아 커뮤니티": "UCy_1qP4yqHqO7c_1G2t1eDg",
    "OpenAI": "UCzvS2F56K8Pz0YVf7qO2YqA",
    "Google DeepMind": "UC766m_h5S6X_FfI76Z2X2_w",
    "Two Minute Papers": "UCbfYPyITQ-7l4upoX8nvctg",
    "Matt Wolfe": "UCX6bY0T-HwT1k5-5sXG545A",
    "AI Explained": "UCNvsCy3W1T-HlRj_N0z200A",
    "The AI Breakdown": "UC_p7mInZ8S_B_p7mInZ8S_A"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

for name, cid in channels.items():
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"{name} ({cid}): {resp.status_code}")
        if resp.status_code == 200:
            print(f"  Content snippet: {resp.text[:100].strip()}")
    except Exception as e:
        print(f"{name}: Error {e}")
