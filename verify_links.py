import json

# 뉴스 데이터 로드
with open('news_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 해외뉴스만 필터링
global_news = [item for item in data if item.get('국가') == '미국']

print(f"총 해외뉴스 개수: {len(global_news)}\n")
print("=" * 80)
print("해외뉴스 링크 샘플 (처음 5개):")
print("=" * 80)

for i, item in enumerate(global_news[:5], 1):
    title = item.get('제목', 'N/A')
    link = item.get('링크', 'N/A')
    media = item.get('매체', 'N/A')
    
    print(f"\n{i}. [{media}]")
    print(f"   제목: {title[:60]}...")
    print(f"   링크: {link}")
    print(f"   링크 상태: {'✓ OK' if link and link.startswith('http') else '✗ 빈 링크'}")

# 통계
links_ok = sum(1 for item in global_news if item.get('링크') and item.get('링크').startswith('http'))
links_empty = len(global_news) - links_ok

print("\n" + "=" * 80)
print(f"링크 통계:")
print(f"  - 정상 링크: {links_ok}개")
print(f"  - 빈 링크: {links_empty}개")
print("=" * 80)
