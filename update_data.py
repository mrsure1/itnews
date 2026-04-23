import json
import os

# 수집된 유튜브 데이터
new_youtube_data = [
  {
    "국가": "유튜브", "매체": "조코딩 JoCoding",
    "제목": "AI뉴스 - Opus 4.7, Claude Design, GPT-5.5, Codex 업데이트, GPT-Image-2, Grok 4.3, Qwen3.6, Video Use 등",
    "링크": "https://www.youtube.com/watch?v=_7orn3F9NHQ",
    "이미지": "https://i.ytimg.com/vi/_7orn3F9NHQ/hqdefault.jpg",
    "요약": "최신 AI 모델 업데이트 소식: Claude Opus 4.7, GPT-5.5 루머, 신규 이미지 생성 모델 활용 전략 등 집대성.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "Universe of AI",
    "제목": "OpenAI LEAKED 5 NEW Models + Two New Agent Platforms + Anthropic REMOVES Claude Code!",
    "링크": "https://www.youtube.com/watch?v=QvXRNdxAsT8",
    "이미지": "https://i.ytimg.com/vi/QvXRNdxAsT8/hqdefault.jpg",
    "요약": "OpenAI의 유출된 5가지 신규 모델 정보와 새로운 에이전트 플랫폼, Anthropic의 Claude Code 변경 사항 분석.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "오후다섯씨",
    "제목": "GPT Images 2 충격🔥 클로드 실험으로 입증! 이렇게 쓰세요! AI 이미지 모델 활용 전략! Claude Code | 나노바나나 | 오후다섯씨",
    "링크": "https://www.youtube.com/watch?v=Qug5Evt1Img",
    "이미지": "https://i.ytimg.com/vi/Qug5Evt1Img/hqdefault.jpg",
    "요약": "나노바나나와 Claude Code를 활용한 최신 AI 이미지 생성 및 전략적 활용법 실습 가이드.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "CodeLucky",
    "제목": "2026년 최고의 AI 글쓰기 도구 10가지: ChatGPT vs Claude vs Gemini (완벽한 비교)",
    "링크": "https://www.youtube.com/watch?v=rt9snA80w4E",
    "이미지": "https://i.ytimg.com/vi/rt9snA80w4E/hqdefault.jpg",
    "요약": "ChatGPT, Claude, Gemini의 글쓰기 성능 완벽 비교. 2026년 기준 최적의 도구 선정.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "AIM Network",
    "제목": "속보 - OpenAI, ChatGPT를 AI 인력으로 전환",
    "링크": "https://www.youtube.com/watch?v=d7tBqfq_6e0",
    "이미지": "https://i.ytimg.com/vi/d7tBqfq_6e0/hqdefault.jpg",
    "요약": "OpenAI가 ChatGPT를 단순 챗봇을 넘어 실제 업무를 수행하는 AI 에이전트 인력으로 전환한다는 소식.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "Mint",
    "제목": "구글 폼 AI '특수팀', 앤트로픽의 클로드 모델을 능가할 전망 | 설명",
    "링크": "https://www.youtube.com/watch?v=37Tp_G1kLEY",
    "이미지": "https://i.ytimg.com/vi/37Tp_G1kLEY/hqdefault.jpg",
    "요약": "구글의 새로운 AI 특수팀 프로젝트가 Anthropic의 Claude 모델을 성능 면에서 추월할 가능성 분석.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "노정석",
    "제목": "EP 94. Claude Opus 4.7 과 낮게 열린 과실들",
    "링크": "https://www.youtube.com/watch?v=DU6gHtt8UZM",
    "이미지": "https://i.ytimg.com/vi/DU6gHtt8UZM/hqdefault.jpg",
    "요약": "Claude Opus 4.7 출시와 함께 우리가 즉시 활용할 수 있는 AI 기회들에 대한 고찰.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "원투코딩 OneTwoCoding",
    "제목": "Claude로 끝내는 하네스 엔지니어링 설계 이론 완벽 정리✔ | 3단계 하네스 엔지니어링 ep.2",
    "링크": "https://www.youtube.com/watch?v=rxLE2MjrHf8",
    "이미지": "https://i.ytimg.com/vi/rxLE2MjrHf8/hqdefault.jpg",
    "요약": "Claude를 엔지니어링 설계에 도입하여 복잡한 시스템 설계를 자동화하고 최적화하는 방법.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "AI Search",
    "제목": "Claude Opus 4.7, Qwen 3.6, Happy Oyster, 실시간 3D 세계, 새로운 Google TTS: AI 뉴스",
    "링크": "https://www.youtube.com/watch?v=G8fqduzB5lc",
    "이미지": "https://i.ytimg.com/vi/G8fqduzB5lc/hqdefault.jpg",
    "요약": "실시간 3D 렌더링, 신규 TTS 모델 등 한 주간의 핵심 AI 뉴스 요약.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "Vivek Mishra",
    "제목": "Claude Opus 4.7 Just Dropped and Destroyed Every AI Model",
    "링크": "https://www.youtube.com/watch?v=g1EKRXllnHo",
    "이미지": "https://i.ytimg.com/vi/g1EKRXllnHo/hqdefault.jpg",
    "요약": "기존의 모든 모델을 압도하는 성능으로 출시된 Claude Opus 4.7의 벤치마크 결과 리뷰.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "AIM Network",
    "제목": "ChatGPT가 지고 있다… 그 이유는 다음과 같다",
    "링크": "https://www.youtube.com/watch?v=5ivhMGGA_lI",
    "이미지": "https://i.ytimg.com/vi/5ivhMGGA_lI/hqdefault.jpg",
    "요약": "경쟁 모델들의 추격과 최근 ChatGPT의 점유율 변화에 대한 원인 분석.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "Kevin Stratvert",
    "제목": "OpenClaw 튜토리얼: 코딩 없이 몇 분 만에 나만의 AI 비서 만들기",
    "링크": "https://www.youtube.com/watch?v=5dlqJwFGBn0",
    "이미지": "https://i.ytimg.com/vi/5dlqJwFGBn0/hqdefault.jpg",
    "요약": "노코딩 툴 OpenClaw를 사용하여 누구나 쉽게 개인용 AI 에이전트를 구축하는 튜토리얼.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "jisungs",
    "제목": "카드뉴스 자동화 n8n 만들어 봤습니다.",
    "링크": "https://www.youtube.com/watch?v=SiyJkAQefNI",
    "이미지": "https://i.ytimg.com/vi/SiyJkAQefNI/hqdefault.jpg",
    "요약": "n8n 워크플로우를 이용해 인스타그램용 카드뉴스를 자동으로 생성하고 업로드하는 시스템 구축기.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "데이터팝콘 data.popcorn",
    "제목": "반복 업무로 오늘도 야근 당첨? 『n8n이 다 해줌』",
    "링크": "https://www.youtube.com/watch?v=wi1TEGm7CTc",
    "이미지": "https://i.ytimg.com/vi/wi1TEGm7CTc/hqdefault.jpg",
    "요약": "직장인들의 반복적인 업무를 n8n 자동화로 해결하여 업무 효율을 극대화하는 실전 팁.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "숏허브 플리 자동화 에이전트",
    "제목": "초보 클릭 한 번 → 플레이리스트채널 노하우 (자동화 무료 공개)",
    "링크": "https://www.youtube.com/watch?v=8NvnCMNbEaU",
    "이미지": "https://i.ytimg.com/vi/8NvnCMNbEaU/hqdefault.jpg",
    "요약": "AI를 활용해 유튜브 플레이리스트 채널 운영을 100% 자동화하는 노하우 공개.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "세바시 강연 Sebasi Talk",
    "제목": "AI 전환, 이것 하나 모르면 대부분 실패합니다 | 조용민 | AI 에이전트",
    "링크": "https://www.youtube.com/watch?v=FRhf2cym5ss",
    "이미지": "https://i.ytimg.com/vi/FRhf2cym5ss/hqdefault.jpg",
    "요약": "구글 조용민 상무가 전하는 AI 에이전트 시대의 생존 전략과 핵심 마인드셋.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "The AI Doctor",
    "제목": "완벽 튜토리얼: Claude Cowork, Seedance 2.0 및 n8n을 사용하여 TikTok 자동화하기",
    "링크": "https://www.youtube.com/watch?v=TjRuxt8Nwss",
    "이미지": "https://i.ytimg.com/vi/TjRuxt8Nwss/hqdefault.jpg",
    "요약": "Claude와 n8n을 연동하여 틱톡 콘텐츠 생성부터 업로드까지 풀 자동화하는 방법.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "The AI Chronicle",
    "제목": "골드만삭스: AI로 인해 미국에서 매달 1만 6천 개의 일자리가 순감하고 있다",
    "링크": "https://www.youtube.com/watch?v=Xl7TgI1X2_o",
    "이미지": "https://i.ytimg.com/vi/Xl7TgI1X2_o/hqdefault.jpg",
    "요약": "AI 기술 발전이 노동 시장에 미치는 실제 경제적 영향과 일자리 감소 통계 분석.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "Adobe",
    "제목": "둘째 날 기조연설 | 어도비 서밋 2026 | 어도비",
    "링크": "https://www.youtube.com/watch?v=k55lrt7yA1A",
    "이미지": "https://i.ytimg.com/vi/k55lrt7yA1A/hqdefault.jpg",
    "요약": "어도비의 생성형 AI '파이어플라이'와 크리에이티브 클라우드의 신기능 발표 현장.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "조코딩 JoCoding",
    "제목": "[AI 뉴스] 메타 라마 4 출시 임박? 애플의 새로운 AI 전략",
    "링크": "https://www.youtube.com/watch?v=P3jFI-VpyLg",
    "이미지": "https://i.ytimg.com/vi/P3jFI-VpyLg/hqdefault.jpg",
    "요약": "Llama 4 출시 소문과 애플 인텔리전스의 향후 방향성 등 메이저 IT 기업 동향 요약.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "The AI Doctor",
    "제목": "이 AI 에이전트는 당신이 신경 쓸 필요 없이 모든 것을 처리합니다…",
    "링크": "https://www.youtube.com/watch?v=UWmp2j3lIOw",
    "이미지": "https://i.ytimg.com/vi/UWmp2j3lIOw/hqdefault.jpg",
    "요약": "자율 주행 AI 에이전트의 발전 수준과 실제 업무 적용 사례 소개.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "Pro Coder",
    "제목": "Claude Opus 4.7이 출시되었는데, 모든 걸 뒤흔들어 놓고 있습니다.",
    "링크": "https://www.youtube.com/watch?v=NSB-_Nm9kfc",
    "이미지": "https://i.ytimg.com/vi/NSB-_Nm9kfc/hqdefault.jpg",
    "요약": "개발자 관점에서 본 Claude Opus 4.7의 성능 향상과 코딩 능력 분석.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "Stephanie Nyarko",
    "제목": "Claude Managed Agents와 n8n 중 어떤 것을 사용해야 할까요?",
    "링크": "https://www.youtube.com/watch?v=xbWN7rvMzrw",
    "이미지": "https://i.ytimg.com/vi/xbWN7rvMzrw/hqdefault.jpg",
    "요약": "Anthropic의 매니지드 에이전트 서비스와 오픈소스 n8n의 장단점 비교.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "The AI Doctor",
    "제목": "이 AI 에이전트가 기존 콘텐츠 전략을 완전히 뒤집어 놓았습니다",
    "링크": "https://www.youtube.com/watch?v=jw4WaiUeNXE",
    "이미지": "https://i.ytimg.com/vi/jw4WaiUeNXE/hqdefault.jpg",
    "요약": "AI를 활용한 콘텐츠 마케팅 전략의 혁명적인 변화와 성공 사례 공유.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  },
  {
    "국가": "유튜브", "매체": "The AI Chronicle",
    "제목": "Sarvam AI, 기업 가치 15억 달러 달성 — + AI 관련 소식 9가지 더",
    "링크": "https://www.youtube.com/watch?v=5BV18zewWKs",
    "이미지": "https://i.ytimg.com/vi/5BV18zewWKs/hqdefault.jpg",
    "요약": "글로벌 AI 스타트업들의 펀딩 규모와 시장 가치 상승 트렌드 분석.",
    "수집일시": "2026-04-23T21:40:00", "type": "youtube"
  }
]

# JSON 파일 업데이트
json_path = 'd:/MrSure/itnews/news_data.json'
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 기존 유튜브 아이템 제거
data = [item for item in data if item.get('type') != 'youtube']

# 새로운 유튜브 아이템 추가 (맨 앞에 배치)
data = new_youtube_data + data

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# JS 파일 업데이트
js_path = 'd:/MrSure/itnews/news_data.js'
with open(js_path, 'w', encoding='utf-8') as f:
    f.write(f"window.NEWS_DATA = {json.dumps(data, ensure_ascii=False, indent=2)};")

print("Successfully updated news_data.json and news_data.js with 30 latest YouTube videos.")
