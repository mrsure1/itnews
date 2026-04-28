"""_is_ai_relevant_youtube 단위 검증 (unittest 표준 라이브러리)."""

import unittest

from collect_news import GLOBAL_OFFICIAL_CHANNELS, _is_ai_relevant_youtube


class TestYoutubeAiRelevance(unittest.TestCase):
    def test_kw_search_rejects_news_shorts(self) -> None:
        bad1 = "승객 83명 두고 출발하자 활주로 뛰어든 사람들 [이슈한컷] #shorts / YTN"
        self.assertFalse(_is_ai_relevant_youtube(bad1, "YTN", "", "kw_search"))
        bad2 = "'왜 나 안태우고 가!' 프랑스서 승객들 활주로 난입 [현장영상] / 채널A"
        self.assertFalse(_is_ai_relevant_youtube(bad2, "채널A", "", "kw_search"))

    def test_kw_search_channel_only_korean_does_not_pass(self) -> None:
        """채널명만 한글이어도 제목·설명에 AI 신호가 없으면 제외."""
        self.assertFalse(
            _is_ai_relevant_youtube("일반 뉴스 제목", "YTN", "구독 좋아요 부탁드립니다.", "kw_search")
        )

    def test_kw_search_accepts_explicit_ai(self) -> None:
        self.assertTrue(
            _is_ai_relevant_youtube("ChatGPT 사용법 초보", "코딩채널", "설명 없음", "kw_search")
        )
        self.assertTrue(
            _is_ai_relevant_youtube("오늘 영상", "테크", "이번엔 Claude API 를 써봤습니다.", "kw_search")
        )
        self.assertTrue(
            _is_ai_relevant_youtube("Gemini 2.5 발표", "구글", "", "kw_search")
        )
        self.assertTrue(
            _is_ai_relevant_youtube("에디터 소개", "개발", "Cursor 로 생산성 올리기", "kw_search")
        )
        self.assertTrue(
            _is_ai_relevant_youtube("영상 제목", "AI", "Runway Gen-3 후기", "kw_search")
        )

    def test_global_official_trusts_whitelist(self) -> None:
        self.assertTrue(_is_ai_relevant_youtube("아무 제목", "OpenAI", "", "global_official"))
        self.assertIn("OpenAI", GLOBAL_OFFICIAL_CHANNELS)

    def test_global_official_rejects_unknown_channel(self) -> None:
        self.assertFalse(_is_ai_relevant_youtube("제목", "YTN", "", "global_official"))


if __name__ == "__main__":
    unittest.main()
