Place your company image variants here.

Supported file types:
- .png
- .jpg / .jpeg
- .webp
- .svg
- .gif

Naming rules (recommended):
- <company-id>-v1.jpg
- <company-id>-v2.jpg
- <company-id>-v3.jpg
- <company-id>-v4.jpg
- <company-id>-v5.jpg

Alternative names also work:
- <company-id>_v1.png
- <company-id>-1.png
- <company-id>_2.jpg

You can also use a subfolder:
- company_images/<company-id>/1.jpg
- company_images/<company-id>/2.jpg

Known company IDs in collect_news.py:
- kakao
- naver
- samsung
- lg
- sk
- apple
- google
- microsoft
- openai
- nvidia
- tesla
- meta
- amazon

Behavior:
- If local images exist for a company ID, they are used first.
- If images are 부족하면, 스크립트가 기업명 기반 검색으로 자동 이미지를 채워서(기본 10장) 저장합니다.
- 자동 수집 파일은 company_images/<company-id>/auto-*.{ext} 형태로 저장됩니다.
- 기본 선택은 날짜 기반 회전이라, 같은 기사도 날짜가 바뀌면 다른 이미지가 선택될 수 있습니다.
- 검색으로도 못 채우면 마지막으로 generated_images/company_variants/의 로고 변형 SVG를 사용합니다.
