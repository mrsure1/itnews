import json
import os

try:
    if not os.path.exists('news_data.json'):
        print("[ERR] news_data.json not found.")
        exit(1)

    with open('news_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    global_news = [x for x in data if x.get('국가') == '미국' or x.get('country') == 'global']
    
    print(f"Total Global News: {len(global_news)}")
    
    # OpenAI Top Check
    top_items = global_news[:10]
    openai_count = 0
    print("\n[Top 10 Global News]")
    for i, item in enumerate(top_items):
        title = (item.get('제목') or item.get('title') or "").strip()
        media = (item.get('매체') or item.get('media') or "").strip()
        is_openai = 'openai' in title.lower() or 'openai' in media.lower()
        marker = " [OPENAI]" if is_openai else ""
        print(f"{i+1}. [{media}] {title[:60]}...{marker}")
        if is_openai:
            openai_count += 1
            
    if openai_count > 0:
        if 'openai' in (global_news[0].get('매체') or "").lower() or 'openai' in (global_news[0].get('제목') or "").lower():
             print("\n[PASS] OpenAI news is at the VERY TOP.")
        else:
             print("\n[WARN] OpenAI news found in top 10, but NOT at the very top (or 1st item is not OpenAI).")
    else:
        print("\n[WARN] No OpenAI news found in top 10.")
        
    # Source Check
    sources = set(x.get('매체') or x.get('media') for x in global_news)
    required = {'Hacker News', 'OpenAI Blog', 'Google DeepMind', 'Google Research', 'Microsoft Research'}
    
    found = sources.intersection(required)
    missing = required - sources
    
    print(f"\nFound Target Sources: {found}")
    if missing:
        print(f"Missing Target Sources: {missing}")
    else:
        print("All target sources found.")

except Exception as e:
    print(f"[ERR] Validation failed: {e}")
