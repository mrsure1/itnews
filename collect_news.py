import base64
import hashlib
import html
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except Exception:
    genai = None

load_dotenv()


def get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def get_csv_env_set(name: str) -> set[str]:
    return {part.strip().lower() for part in os.getenv(name, "").split(",") if part.strip()}


def get_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
IMAGE_OUTPUT_DIR = Path(os.getenv("NEWS_IMAGE_DIR", "generated_images"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_PROMPT_MODEL = os.getenv("GEMINI_PROMPT_MODEL", "gemini-2.5-flash")
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")
NEWS_IMAGE_STYLE = os.getenv(
    "NEWS_IMAGE_STYLE",
    (
        "high-quality 3D render, futuristic IT newsroom illustration, "
        "isometric composition, cinematic lighting, clean background, "
        "no brand logos, no text overlay"
    ),
).strip()
NEWS_AI_IMAGE_LIMIT = get_int_env("NEWS_AI_IMAGE_LIMIT", 5)
KEYWORD_TEMPLATE_ENABLED = get_bool_env("KEYWORD_TEMPLATE_ENABLED", False)
KEYWORD_PHOTO_ENABLED = get_bool_env("KEYWORD_PHOTO_ENABLED", True)
KEYWORD_STOCK_ENABLED = get_bool_env("KEYWORD_STOCK_ENABLED", True)
KEYWORD_STOCK_TIMEOUT = get_int_env("KEYWORD_STOCK_TIMEOUT", 20)
MIN_STOCK_IMAGE_BYTES = get_int_env("MIN_STOCK_IMAGE_BYTES", 1500)
KEYWORD_REPRESENTATIVE_QUERY_ENABLED = get_bool_env("KEYWORD_REPRESENTATIVE_QUERY_ENABLED", True)
IMAGE_DEDUP_IN_RUN = get_bool_env("IMAGE_DEDUP_IN_RUN", True)
COMPANY_LOGO_PRIORITY_MODE = get_bool_env("COMPANY_LOGO_PRIORITY_MODE", True)
USE_RSS_SOURCE_IMAGE = get_bool_env("USE_RSS_SOURCE_IMAGE", True)
COMPANY_VARIANT_COUNT = max(1, min(5, get_int_env("COMPANY_VARIANT_COUNT", 5)))
COMPANY_LOCAL_IMAGE_MODE = get_bool_env("COMPANY_LOCAL_IMAGE_MODE", True)
COMPANY_IMAGE_POOL_DIR = Path(os.getenv("COMPANY_IMAGE_POOL_DIR", "company_images"))
COMPANY_SEARCH_IMAGE_ENABLED = get_bool_env("COMPANY_SEARCH_IMAGE_ENABLED", True)
COMPANY_SEARCH_IMAGE_TARGET = max(3, min(20, get_int_env("COMPANY_SEARCH_IMAGE_TARGET", 10)))
COMPANY_SEARCH_TIMEOUT = get_int_env("COMPANY_SEARCH_TIMEOUT", 12)
COMPANY_DAILY_ROTATION = get_bool_env("COMPANY_DAILY_ROTATION", True)
COMPANY_INFER_FROM_ENGLISH_TITLE = get_bool_env("COMPANY_INFER_FROM_ENGLISH_TITLE", False)
NEWS_CURATION_ENABLED = get_bool_env("NEWS_CURATION_ENABLED", True)
NEWS_CURATION_LIMIT = get_int_env("NEWS_CURATION_LIMIT", 20)
RSS_IMAGE_FORCE_ALLOW_SOURCES = get_csv_env_set("RSS_IMAGE_FORCE_ALLOW_SOURCES")
RSS_IMAGE_FORCE_DENY_SOURCES = get_csv_env_set("RSS_IMAGE_FORCE_DENY_SOURCES")

_ai_image_count = 0
_curation_count = 0
_gemini_text_model_name = ""
_gemini_text_model = None
_used_image_hashes_in_run: set[str] = set()
_used_remote_image_urls_in_run: set[str] = set()
_company_logo_data_uri_cache: dict[str, str] = {}
_company_variant_paths_cache: dict[str, list[str]] = {}
_company_variant_source_cache: dict[str, str] = {}
_company_last_variant_index: dict[str, int] = {}
_company_catalog_cache: list[dict] | None = None

# Korean keys/values kept as Unicode escapes to avoid terminal encoding issues.
KEY_COUNTRY = "\uad6d\uac00"
KEY_MEDIA = "\ub9e4\uccb4"
KEY_TITLE = "\uc81c\ubaa9"
KEY_LINK = "\ub9c1\ud06c"
KEY_SUMMARY = "\uc694\uc57d"
KEY_IMAGE = "\uc774\ubbf8\uc9c0"
KEY_COLLECTED_AT = "\uc218\uc9d1\uc77c\uc2dc"
KEY_IMAGE_PROMPT = "\uc774\ubbf8\uc9c0\ud504\ub86c\ud504\ud2b8"
KEY_IMAGE_PROVIDER = "\uc774\ubbf8\uc9c0\uc0dd\uc131\ubc29\uc2dd"

VAL_DOMESTIC = "\uad6d\ub0b4"
VAL_US = "\ubbf8\uad6d"
VAL_NAVER_NEWS = "\ub124\uc774\ubc84 \ub274\uc2a4"

KEYWORD_THEMES = [
    {
        "id": "ai",
        "label": "AI",
        "subtitle": "Artificial Intelligence",
        "colors": ("#0f172a", "#2563eb", "#22d3ee"),
        "keywords": [
            "ai",
            "artificial intelligence",
            "인공지능",
            "생성형",
            "llm",
            "gpt",
            "gemini",
            "agent",
            "에이전트",
            "온디바이스 ai",
        ],
    },
    {
        "id": "security",
        "label": "SECURITY",
        "subtitle": "Cyber Security",
        "colors": ("#111827", "#334155", "#06b6d4"),
        "keywords": [
            "보안",
            "사이버",
            "해킹",
            "랜섬웨어",
            "피싱",
            "malware",
            "hack",
            "security",
            "vulnerability",
            "취약점",
        ],
    },
    {
        "id": "semiconductor",
        "label": "CHIP",
        "subtitle": "Semiconductor",
        "colors": ("#1e1b4b", "#4338ca", "#a78bfa"),
        "keywords": [
            "반도체",
            "chip",
            "칩",
            "gpu",
            "npu",
            "hbm",
            "파운드리",
            "foundry",
            "메모리",
            "memory",
        ],
    },
    {
        "id": "mobile",
        "label": "MOBILE",
        "subtitle": "Smart Device",
        "colors": ("#0f172a", "#0ea5e9", "#38bdf8"),
        "keywords": [
            "스마트폰",
            "휴대폰",
            "아이폰",
            "iphone",
            "android",
            "안드로이드",
            "갤럭시",
            "ios",
            "웨어러블",
            "smartphone",
        ],
    },
    {
        "id": "cloud",
        "label": "CLOUD",
        "subtitle": "Cloud Infra",
        "colors": ("#082f49", "#0284c7", "#7dd3fc"),
        "keywords": [
            "클라우드",
            "cloud",
            "saas",
            "server",
            "데이터센터",
            "data center",
            "인프라",
            "infra",
        ],
    },
    {
        "id": "robotics",
        "label": "ROBOTICS",
        "subtitle": "Robotics & Automation",
        "colors": ("#022c22", "#059669", "#34d399"),
        "keywords": [
            "로봇",
            "robot",
            "automation",
            "자동화",
            "드론",
            "drone",
        ],
    },
    {
        "id": "gaming",
        "label": "GAMING",
        "subtitle": "Game Industry",
        "colors": ("#2e1065", "#7c3aed", "#c4b5fd"),
        "keywords": [
            "게임",
            "game",
            "콘솔",
            "xbox",
            "playstation",
            "닌텐도",
            "steam",
        ],
    },
    {
        "id": "space",
        "label": "SPACE",
        "subtitle": "Space Tech",
        "colors": ("#172554", "#1d4ed8", "#60a5fa"),
        "keywords": [
            "우주",
            "space",
            "위성",
            "satellite",
            "nasa",
            "rocket",
            "로켓",
        ],
    },
]

COMPANY_THEMES = [
    {
        "id": "kakao",
        "label": "KAKAO",
        "subtitle": "Kakao",
        "keywords": ["카카오", "kakao", "카톡", "kakaotalk"],
        "search_queries": [
            "kakaotalk smartphone app",
            "korean mobile messenger app",
            "south korea tech company office",
        ],
        "stock_tags": [
            "korea,office,technology",
            "startup,office,teamwork",
            "mobile,app,technology",
        ],
        "prompt_subject": "a modern Korean internet company office scene",
    },
    {
        "id": "naver",
        "label": "NAVER",
        "subtitle": "Naver",
        "keywords": ["네이버", "naver", "라인", "line messenger"],
        "search_queries": [
            "search engine technology office",
            "korean internet company workspace",
            "messenger app smartphone usage",
        ],
        "stock_tags": [
            "search,technology,office",
            "korea,tech,workspace",
            "mobile,app,productivity",
        ],
        "prompt_subject": "a leading search and platform company workspace",
    },
    {
        "id": "samsung",
        "label": "SAMSUNG",
        "subtitle": "Samsung",
        "keywords": ["삼성", "samsung", "갤럭시"],
        "search_queries": [
            "smartphone product photography",
            "semiconductor chip laboratory",
            "consumer electronics showcase",
        ],
        "stock_tags": [
            "smartphone,electronics,technology",
            "semiconductor,electronics,lab",
            "display,technology,innovation",
        ],
        "prompt_subject": "a global electronics company R&D environment",
    },
    {
        "id": "lg",
        "label": "LG",
        "subtitle": "LG",
        "keywords": ["lg", "엘지", "lg유플러스", "lgu+", "lgu+"],
        "search_queries": [
            "telecommunications network infrastructure",
            "consumer electronics home devices",
            "korean technology company office",
        ],
        "stock_tags": [
            "telecom,technology,office",
            "electronics,home,technology",
            "network,infrastructure,technology",
        ],
        "prompt_subject": "a telecom and electronics company innovation center",
    },
    {
        "id": "sk",
        "label": "SK",
        "subtitle": "SK",
        "keywords": ["skt", "sk텔레콤", "sk telecom", "sk하이닉스", "sk hynix"],
        "search_queries": [
            "telecom network engineers",
            "semiconductor production facility",
            "mobile network technology",
        ],
        "stock_tags": [
            "telecom,network,technology",
            "semiconductor,factory,technology",
            "data,ai,infrastructure",
        ],
        "prompt_subject": "a telecom and semiconductor company operations scene",
    },
    {
        "id": "apple",
        "label": "APPLE",
        "subtitle": "Apple",
        "keywords": ["애플", "apple", "iphone", "ios", "mac"],
        "search_queries": [
            "iphone smartphone product photo",
            "minimal laptop workspace setup",
            "premium consumer electronics",
        ],
        "stock_tags": [
            "smartphone,minimal,technology",
            "laptop,workspace,technology",
            "wearable,consumer,electronics",
        ],
        "prompt_subject": "a premium consumer tech product launch environment",
    },
    {
        "id": "google",
        "label": "GOOGLE",
        "subtitle": "Google",
        "keywords": ["구글", "google", "android", "pixel", "youtube"],
        "search_queries": [
            "android smartphone interface",
            "search technology data visualization",
            "cloud ai infrastructure",
        ],
        "stock_tags": [
            "search,data,technology",
            "android,smartphone,technology",
            "ai,cloud,technology",
        ],
        "prompt_subject": "a global search and AI company product lab",
    },
    {
        "id": "microsoft",
        "label": "MICROSOFT",
        "subtitle": "Microsoft",
        "keywords": ["마이크로소프트", "microsoft", "windows", "azure", "copilot"],
        "search_queries": [
            "developer laptop coding workspace",
            "enterprise cloud data center",
            "business software office environment",
        ],
        "stock_tags": [
            "software,office,technology",
            "cloud,server,technology",
            "developer,code,workspace",
        ],
        "prompt_subject": "a software and cloud company engineering floor",
    },
    {
        "id": "openai",
        "label": "OPENAI",
        "subtitle": "OpenAI",
        "keywords": ["openai", "챗gpt", "chatgpt", "gpt"],
        "search_queries": [
            "artificial intelligence research lab",
            "machine learning engineers working",
            "ai server hardware racks",
        ],
        "stock_tags": [
            "ai,server,technology",
            "machine-learning,research,technology",
            "data-center,ai,infrastructure",
        ],
        "prompt_subject": "an advanced AI research company environment",
    },
    {
        "id": "nvidia",
        "label": "NVIDIA",
        "subtitle": "NVIDIA",
        "keywords": ["엔비디아", "nvidia", "cuda", "rtx", "geforce"],
        "search_queries": [
            "gpu graphics card closeup",
            "ai accelerator server hardware",
            "high performance computing datacenter",
        ],
        "stock_tags": [
            "gpu,computer,technology",
            "datacenter,server,technology",
            "electronics,circuit,hardware",
        ],
        "prompt_subject": "a GPU and AI hardware engineering environment",
    },
    {
        "id": "tesla",
        "label": "TESLA",
        "subtitle": "Tesla",
        "keywords": ["테슬라", "tesla", "자율주행", "fsd"],
        "search_queries": [
            "electric vehicle technology",
            "autonomous driving car sensors",
            "modern EV charging station",
        ],
        "stock_tags": [
            "electric-car,technology,transport",
            "autonomous,vehicle,innovation",
            "battery,energy,technology",
        ],
        "prompt_subject": "an electric vehicle technology demonstration scene",
    },
    {
        "id": "meta",
        "label": "META",
        "subtitle": "Meta",
        "keywords": ["메타", "meta", "facebook", "instagram", "threads"],
        "search_queries": [
            "social media smartphone app",
            "virtual reality headset technology",
            "internet platform office workspace",
        ],
        "stock_tags": [
            "social-media,smartphone,technology",
            "vr,headset,technology",
            "office,software,technology",
        ],
        "prompt_subject": "a social platform and mixed-reality product workspace",
    },
    {
        "id": "amazon",
        "label": "AMAZON",
        "subtitle": "Amazon",
        "keywords": ["아마존", "amazon", "aws", "prime", "알렉사", "alexa"],
        "search_queries": [
            "cloud computing datacenter",
            "warehouse automation robotics",
            "smart speaker home device",
        ],
        "stock_tags": [
            "cloud,server,technology",
            "warehouse,robotics,automation",
            "smart-home,device,technology",
        ],
        "prompt_subject": "a cloud and automation technology operations scene",
    },
]

COMPANY_LOGO_DOMAINS = {
    "kakao": "kakao.com",
    "naver": "navercorp.com",
    "samsung": "samsung.com",
    "lg": "lg.com",
    "sk": "sktelecom.com",
    "apple": "apple.com",
    "google": "google.com",
    "microsoft": "microsoft.com",
    "openai": "openai.com",
    "nvidia": "nvidia.com",
    "tesla": "tesla.com",
    "meta": "meta.com",
    "amazon": "amazon.com",
    "anthropic": "anthropic.com",
    "xai": "x.ai",
    "deepmind": "deepmind.google",
    "deepseek": "deepseek.com",
    "intel": "intel.com",
    "amd": "amd.com",
    "qualcomm": "qualcomm.com",
    "tsmc": "tsmc.com",
    "arm": "arm.com",
    "broadcom": "broadcom.com",
    "oracle": "oracle.com",
    "ibm": "ibm.com",
    "adobe": "adobe.com",
    "salesforce": "salesforce.com",
    "sap": "sap.com",
    "palantir": "palantir.com",
    "uber": "uber.com",
    "airbnb": "airbnb.com",
    "netflix": "netflix.com",
    "sony": "sony.com",
    "nintendo": "nintendo.com",
    "softbank": "softbank.jp",
    "huawei": "huawei.com",
    "xiaomi": "xiaomi.com",
    "lenovo": "lenovo.com",
    "baidu": "baidu.com",
    "tencent": "tencent.com",
    "alibaba": "alibaba.com",
    "bytedance": "bytedance.com",
    "hyundai": "hyundai.com",
    "kia": "kia.com",
    "posco": "posco.com",
    "hanwha": "hanwha.com",
    "lotte": "lotte.co.kr",
    "cj": "cj.net",
    "kt": "kt.com",
    "coupang": "coupang.com",
    "nhn": "nhn.com",
    "nexon": "nexon.com",
    "krafton": "krafton.com",
    "ncsoft": "ncsoft.com",
    "pearlabyss": "pearlabyss.com",
    "asml": "asml.com",
    "siemens": "siemens.com",
    "bosch": "bosch.com",
}

COMPANY_EXTRA_CATALOG = [
    {"id": "anthropic", "name": "Anthropic", "aliases": ["anthropic", "claude"]},
    {"id": "xai", "name": "xAI", "aliases": ["xai", "x.ai", "grok"]},
    {"id": "deepmind", "name": "DeepMind", "aliases": ["deepmind", "google deepmind"]},
    {"id": "deepseek", "name": "DeepSeek", "aliases": ["deepseek"]},
    {"id": "intel", "name": "Intel", "aliases": ["intel", "인텔"]},
    {"id": "amd", "name": "AMD", "aliases": ["amd", "라이젠", "radeon"]},
    {"id": "qualcomm", "name": "Qualcomm", "aliases": ["qualcomm", "퀄컴", "snapdragon"]},
    {"id": "tsmc", "name": "TSMC", "aliases": ["tsmc"]},
    {"id": "arm", "name": "ARM", "aliases": ["arm", "arm holdings"]},
    {"id": "broadcom", "name": "Broadcom", "aliases": ["broadcom"]},
    {"id": "oracle", "name": "Oracle", "aliases": ["oracle", "오라클"]},
    {"id": "ibm", "name": "IBM", "aliases": ["ibm"]},
    {"id": "adobe", "name": "Adobe", "aliases": ["adobe", "어도비"]},
    {"id": "salesforce", "name": "Salesforce", "aliases": ["salesforce", "세일즈포스"]},
    {"id": "sap", "name": "SAP", "aliases": ["sap"]},
    {"id": "palantir", "name": "Palantir", "aliases": ["palantir"]},
    {"id": "uber", "name": "Uber", "aliases": ["uber"]},
    {"id": "airbnb", "name": "Airbnb", "aliases": ["airbnb"]},
    {"id": "netflix", "name": "Netflix", "aliases": ["netflix", "넷플릭스"]},
    {"id": "sony", "name": "Sony", "aliases": ["sony", "소니"]},
    {"id": "nintendo", "name": "Nintendo", "aliases": ["nintendo", "닌텐도"]},
    {"id": "softbank", "name": "SoftBank", "aliases": ["softbank", "소프트뱅크"]},
    {"id": "huawei", "name": "Huawei", "aliases": ["huawei", "화웨이"]},
    {"id": "xiaomi", "name": "Xiaomi", "aliases": ["xiaomi", "샤오미"]},
    {"id": "lenovo", "name": "Lenovo", "aliases": ["lenovo", "레노버"]},
    {"id": "baidu", "name": "Baidu", "aliases": ["baidu", "바이두"]},
    {"id": "tencent", "name": "Tencent", "aliases": ["tencent", "텐센트"]},
    {"id": "alibaba", "name": "Alibaba", "aliases": ["alibaba", "알리바바"]},
    {"id": "bytedance", "name": "ByteDance", "aliases": ["bytedance", "틱톡", "tiktok"]},
    {"id": "hyundai", "name": "Hyundai", "aliases": ["현대", "hyundai", "현대차"]},
    {"id": "kia", "name": "Kia", "aliases": ["기아", "kia"]},
    {"id": "posco", "name": "POSCO", "aliases": ["포스코", "posco"]},
    {"id": "hanwha", "name": "Hanwha", "aliases": ["한화", "hanwha"]},
    {"id": "lotte", "name": "Lotte", "aliases": ["롯데", "lotte"]},
    {"id": "cj", "name": "CJ", "aliases": ["cj", "씨제이"]},
    {"id": "kt", "name": "KT", "aliases": ["kt", "케이티"]},
    {"id": "coupang", "name": "Coupang", "aliases": ["쿠팡", "coupang"]},
    {"id": "nhn", "name": "NHN", "aliases": ["nhn"]},
    {"id": "nexon", "name": "Nexon", "aliases": ["넥슨", "nexon"]},
    {"id": "krafton", "name": "Krafton", "aliases": ["크래프톤", "krafton"]},
    {"id": "ncsoft", "name": "NCSoft", "aliases": ["엔씨소프트", "ncsoft"]},
    {"id": "pearlabyss", "name": "Pearl Abyss", "aliases": ["펄어비스", "pearl abyss", "pearlabyss"]},
    {"id": "asml", "name": "ASML", "aliases": ["asml"]},
    {"id": "siemens", "name": "Siemens", "aliases": ["siemens"]},
    {"id": "bosch", "name": "Bosch", "aliases": ["bosch"]},
]

KEYWORD_THEME_SEARCH_QUERIES = {
    "ai": [
        "artificial intelligence workstation",
        "machine learning engineer desk",
        "ai chip server room",
    ],
    "security": [
        "cyber security operations center",
        "digital lock computer screen",
        "security analyst monitoring dashboard",
    ],
    "semiconductor": [
        "semiconductor wafer fabrication",
        "computer chip macro photo",
        "electronics circuit board closeup",
    ],
    "mobile": [
        "smartphone product photography",
        "person using mobile app",
        "phone on desk natural light",
    ],
    "cloud": [
        "cloud datacenter server racks",
        "enterprise server room",
        "network infrastructure operations",
    ],
    "robotics": [
        "industrial robot arm factory",
        "humanoid robot technology",
        "automation equipment workplace",
    ],
    "gaming": [
        "gaming pc setup desk",
        "console controller closeup",
        "esports gaming room",
    ],
    "space": [
        "satellite in space",
        "rocket launch night",
        "earth orbit technology",
    ],
}

if genai is not None and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception:
        pass


def slugify(value: str, max_len: int = 40) -> str:
    # Keep filenames OS-safe across locales by using ASCII slug + hash suffix.
    slug = re.sub(r"[^0-9A-Za-z]+", "-", value).strip("-").lower()
    return (slug[:max_len] or "news").strip("-")


def to_web_path(path: Path) -> str:
    return path.as_posix()


def safe_console_text(text: str) -> str:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def sanitize_url(url: str) -> str:
    if not url:
        return ""
    value = url.strip()
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return ""


def get_image_digest(content: bytes) -> str:
    return hashlib.sha1(content).hexdigest()


def claim_image_bytes_for_run(content: bytes) -> bool:
    if not content:
        return False
    if not IMAGE_DEDUP_IN_RUN:
        return True

    digest = get_image_digest(content)
    if digest in _used_image_hashes_in_run:
        return False
    _used_image_hashes_in_run.add(digest)
    return True


def claim_cached_image_for_run(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        payload = path.read_bytes()
    except Exception:
        return False
    if len(payload) < 256:
        return False
    return claim_image_bytes_for_run(payload)


def remove_file_silent(path: Path):
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


def claim_remote_image_url_for_run(url: str) -> bool:
    value = sanitize_url(url)
    if not value:
        return False
    if not IMAGE_DEDUP_IN_RUN:
        return True
    if value in _used_remote_image_urls_in_run:
        return False
    _used_remote_image_urls_in_run.add(value)
    return True


def fetch_image_payload(url: str, timeout: int) -> bytes:
    try:
        res = requests.get(
            url,
            headers=REQUEST_HEADERS,
            timeout=max(5, timeout),
            allow_redirects=True,
        )
    except Exception:
        return b""

    if not res.ok:
        return b""

    content_type = (res.headers.get("content-type") or "").lower()
    if "image/" not in content_type:
        return b""

    payload = res.content or b""
    if len(payload) < max(512, MIN_STOCK_IMAGE_BYTES):
        return b""

    return payload


def get_tag_text(parent, tag_name: str) -> str:
    if not parent:
        return ""
    tag = parent.find(tag_name)
    if not tag:
        return ""
    return normalize_space(tag.get_text(" ", strip=True))


def clean_summary(text: str) -> str:
    if not text:
        return ""
    try:
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text(" ", strip=True)
    except Exception:
        return text


def clean_feed_text(text: str) -> str:
    value = normalize_space(text or "")
    # Some feeds (e.g., The Verge) expose CDATA markers as plain text.
    if value.startswith("<![CDATA[") and value.endswith("]]>"):
        value = value[len("<![CDATA[") : -len("]]>")]
    return html.unescape(normalize_space(value))


def extract_image_from_rss_item(item_soup, description_html: str) -> str:
    media_content = item_soup.find("media:content")
    if media_content:
        candidate = sanitize_url(media_content.get("url", ""))
        if candidate:
            return candidate

    media_thumbnail = item_soup.find("media:thumbnail")
    if media_thumbnail:
        candidate = sanitize_url(media_thumbnail.get("url", ""))
        if candidate:
            return candidate

    enclosure = item_soup.find("enclosure")
    if enclosure:
        mime = (enclosure.get("type", "") or "").lower()
        if mime.startswith("image/"):
            candidate = sanitize_url(enclosure.get("url", ""))
            if candidate:
                return candidate

    if description_html:
        try:
            desc_soup = BeautifulSoup(description_html, "html.parser")
            image_tag = desc_soup.find("img")
            if image_tag:
                candidate = sanitize_url(image_tag.get("src", ""))
                if candidate:
                    return candidate
        except Exception:
            return ""

    return ""


def extract_feed_policy_meta(channel_soup) -> dict:
    if not channel_soup:
        return {}

    return {
        "copyright": get_tag_text(channel_soup, "copyright"),
        "rights": get_tag_text(channel_soup, "rights") or get_tag_text(channel_soup, "dc:rights"),
        "license": (
            get_tag_text(channel_soup, "creativecommons:license")
            or get_tag_text(channel_soup, "cc:license")
            or get_tag_text(channel_soup, "license")
        ),
        "docs": get_tag_text(channel_soup, "docs"),
    }


def parse_rss_feed(url: str, max_items: int = 10) -> dict:
    """
    Returns: {
      "items": [
        {"title", "link", "description", "description_html", "rss_image_url", "item_rights"}
      ],
      "meta": {"copyright", "rights", "license", "docs"}
    }
    """
    try:
        r = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
        if r.status_code != 200:
            return {"items": [], "meta": {}}

        try:
            soup = BeautifulSoup(r.content, "xml")
        except Exception:
            soup = BeautifulSoup(r.content, "html.parser")
        if not soup.find("item"):
            soup = BeautifulSoup(r.content, "html.parser")

        channel = soup.find("channel")
        feed_root = channel or soup.find("feed")
        feed_meta = extract_feed_policy_meta(feed_root)

        item_nodes = soup.find_all("item")
        atom_mode = False
        if not item_nodes:
            item_nodes = soup.find_all("entry")
            atom_mode = True
        item_nodes = item_nodes[:max_items]

        results: list[dict] = []
        for item in item_nodes:
            title_tag = item.find("title")
            if atom_mode:
                link_tag = item.find("link", attrs={"rel": "alternate"}) or item.find("link")
                desc_tag = item.find("summary") or item.find("content")
            else:
                link_tag = item.find("link")
                desc_tag = item.find("description")

            link_url = ""
            if link_tag:
                link_url = link_tag.get("href", "").strip()
                if not link_url:
                    link_url = link_tag.get_text(strip=True)
                if not link_url and link_tag.next_sibling:
                    sibling = link_tag.next_sibling
                    if isinstance(sibling, str):
                        link_url = sibling.strip()

            description_html = desc_tag.decode_contents() if desc_tag else ""
            description_text = clean_feed_text(clean_summary(description_html))
            rss_image_url = extract_image_from_rss_item(item, description_html)
            item_rights = (
                get_tag_text(item, "media:copyright")
                or get_tag_text(item, "rights")
                or get_tag_text(item, "dc:rights")
                or get_tag_text(item, "creativecommons:license")
                or get_tag_text(item, "cc:license")
            )

            results.append(
                {
                    "title": clean_feed_text(title_tag.get_text(strip=True) if title_tag else ""),
                    "link": sanitize_url(link_url),
                    "description": description_text,
                    "description_html": description_html,
                    "rss_image_url": rss_image_url,
                    "item_rights": item_rights,
                }
            )

        return {"items": results, "meta": feed_meta}
    except Exception as e:
        print(f"RSS parsing error: {e}")
        return {"items": [], "meta": {}}


def has_explicit_image_allowance(text: str) -> bool:
    sample = (text or "").strip().lower()
    if not sample:
        return False

    allow_keywords = (
        "creative commons",
        "creativecommons.org/licenses",
        "cc-by",
        "cc by",
        "cc-by-sa",
        "cc by-sa",
        "public domain",
        "reuse permitted",
        "redistribution permitted",
        "republish permitted",
    )
    deny_keywords = (
        "all rights reserved",
        "do not reproduce",
        "no redistribution",
        "unauthorized reproduction prohibited",
    )

    has_allow = any(keyword in sample for keyword in allow_keywords)
    has_deny = any(keyword in sample for keyword in deny_keywords)
    return has_allow and not has_deny


def feed_explicitly_allows_rss_images(feed_meta: dict) -> bool:
    text_blob = " ".join(
        filter(
            None,
            [
                feed_meta.get("license", ""),
                feed_meta.get("rights", ""),
                feed_meta.get("copyright", ""),
                feed_meta.get("docs", ""),
            ],
        )
    )
    return has_explicit_image_allowance(text_blob)


def should_use_rss_source_image(
    source_name: str,
    rss_image_url: str,
    feed_allows: bool,
    item_rights: str,
) -> bool:
    if not rss_image_url:
        return False

    source_key = source_name.strip().lower()
    if source_key in RSS_IMAGE_FORCE_DENY_SOURCES:
        return False
    if source_key in RSS_IMAGE_FORCE_ALLOW_SOURCES:
        return True

    if has_explicit_image_allowance(item_rights):
        return True
    return feed_allows


def get_company_catalog() -> list[dict]:
    global _company_catalog_cache
    if _company_catalog_cache is not None:
        return _company_catalog_cache

    merged: dict[str, dict] = {}

    for theme in COMPANY_THEMES:
        theme_id = (theme.get("id") or "").strip().lower()
        if not theme_id:
            continue
        entry = merged.setdefault(
            theme_id,
            {
                "id": theme_id,
                "name": theme.get("subtitle") or theme.get("label") or theme_id,
                "label": theme.get("label") or (theme.get("subtitle") or theme_id).upper(),
                "subtitle": theme.get("subtitle") or theme.get("label") or theme_id,
                "domain": COMPANY_LOGO_DOMAINS.get(theme_id, ""),
                "aliases": [],
            },
        )
        for keyword in theme.get("keywords", []):
            kw = (keyword or "").strip()
            if kw:
                entry["aliases"].append(kw)

    for company in COMPANY_EXTRA_CATALOG:
        company_id = (company.get("id") or "").strip().lower()
        if not company_id:
            continue
        entry = merged.setdefault(
            company_id,
            {
                "id": company_id,
                "name": company.get("name") or company_id,
                "label": (company.get("name") or company_id).upper(),
                "subtitle": company.get("name") or company_id,
                "domain": COMPANY_LOGO_DOMAINS.get(company_id, ""),
                "aliases": [],
            },
        )
        entry["name"] = company.get("name") or entry.get("name") or company_id
        entry["label"] = (entry["name"] or company_id).upper()
        entry["subtitle"] = entry["name"] or company_id
        entry["domain"] = company.get("domain") or entry.get("domain") or COMPANY_LOGO_DOMAINS.get(company_id, "")
        for alias in company.get("aliases", []):
            al = (alias or "").strip()
            if al:
                entry["aliases"].append(al)

    catalog: list[dict] = []
    for entry in merged.values():
        aliases = [(a or "").strip() for a in entry.get("aliases", []) if (a or "").strip()]
        aliases.append(entry.get("name", ""))
        aliases.append(entry.get("id", ""))

        # Stable de-dup preserving order, then prefer longer aliases for matching precision.
        seen: set[str] = set()
        ordered_aliases: list[str] = []
        for alias in aliases:
            k = alias.lower()
            if not k or k in seen:
                continue
            seen.add(k)
            ordered_aliases.append(alias)
        ordered_aliases.sort(key=lambda x: (-len(x), x.lower()))

        catalog.append(
            {
                "id": entry["id"],
                "name": entry.get("name") or entry["id"],
                "label": entry.get("label") or (entry.get("name") or entry["id"]).upper(),
                "subtitle": entry.get("subtitle") or entry.get("name") or entry["id"],
                "domain": entry.get("domain", ""),
                "aliases": ordered_aliases,
            }
        )

    _company_catalog_cache = catalog
    return catalog


def find_alias_position(text_lower: str, alias: str) -> int:
    needle = (alias or "").strip().lower()
    if not needle:
        return -1

    # Use boundaries for ASCII-ish aliases to avoid matching "arm" inside "alarm".
    if re.fullmatch(r"[a-z0-9 .+\-&]+", needle):
        pattern = rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])"
        match = re.search(pattern, text_lower)
        return match.start() if match else -1

    return text_lower.find(needle)


def infer_company_like_token_from_title(title: str) -> str:
    # Fallback for uncatalogued companies in English headlines.
    tokens = re.findall(r"\b[A-Z][A-Za-z0-9&.+-]{2,24}\b", title or "")
    ignore = {
        "The",
        "This",
        "That",
        "Why",
        "How",
        "What",
        "When",
        "Where",
        "Who",
        "Its",
        "Their",
        "US",
        "UK",
        "EU",
        "AI",
        "IT",
        "CEO",
        "CFO",
        "CTO",
        "RSS",
    }
    for token in tokens:
        if token in ignore:
            continue
        return token
    return ""


def find_company_theme_in_title(title: str):
    text_lower = (title or "").lower()
    best_match = None
    for company in get_company_catalog():
        for alias in company.get("aliases", []):
            pos = find_alias_position(text_lower, alias)
            if pos < 0:
                continue
            score = (pos, -len(alias))
            if best_match is None or score < best_match[0]:
                best_match = (score, company, alias)

    if best_match:
        return best_match[1], best_match[2]

    if not COMPANY_INFER_FROM_ENGLISH_TITLE:
        return None, ""

    inferred = infer_company_like_token_from_title(title)
    if not inferred:
        return None, ""

    dynamic_id = slugify(inferred, max_len=24) or "company"
    dynamic_company = {
        "id": dynamic_id,
        "name": inferred,
        "label": inferred.upper(),
        "subtitle": inferred,
        "domain": "",
        "aliases": [inferred],
    }
    return dynamic_company, inferred


def get_company_logo_url(theme: dict) -> str:
    theme_id = (theme.get("id") or "").strip().lower()
    domain = (theme.get("domain") or "").strip().lower() or COMPANY_LOGO_DOMAINS.get(theme_id, "")
    if not domain:
        return ""
    # Remote logo endpoint (Clearbit) - returns brand logo by company domain.
    return f"https://logo.clearbit.com/{domain}?size=512"


def fetch_small_image_payload(url: str, timeout: int, min_bytes: int = 120) -> bytes:
    try:
        res = requests.get(
            url,
            headers=REQUEST_HEADERS,
            timeout=max(5, timeout),
            allow_redirects=True,
        )
    except Exception:
        return b""

    if not res.ok:
        return b""

    content_type = (res.headers.get("content-type") or "").lower()
    if "image/" not in content_type:
        return b""

    payload = res.content or b""
    if len(payload) < max(64, min_bytes):
        return b""
    return payload


def fetch_company_logo_data_uri(theme: dict) -> str:
    theme_id = (theme.get("id") or "").strip().lower()
    if not theme_id:
        return ""
    if theme_id in _company_logo_data_uri_cache:
        return _company_logo_data_uri_cache[theme_id]

    domain = (theme.get("domain") or "").strip().lower() or COMPANY_LOGO_DOMAINS.get(theme_id, "")
    if not domain:
        _company_logo_data_uri_cache[theme_id] = ""
        return ""

    logo_urls = [
        f"https://logo.clearbit.com/{domain}?size=512",
        f"https://logo.clearbit.com/{domain}?size=256",
        f"https://www.google.com/s2/favicons?domain_url={domain}&sz=256",
        f"https://icons.duckduckgo.com/ip3/{domain}.ico",
    ]

    for logo_url in logo_urls:
        payload = fetch_small_image_payload(logo_url, timeout=10, min_bytes=120)
        if not payload:
            continue
        ext = Path(logo_url.split("?")[0]).suffix.lower()
        if ext == ".svg":
            mime = "image/svg+xml"
        elif ext == ".ico":
            mime = "image/x-icon"
        else:
            mime = "image/png"
        b64 = base64.b64encode(payload).decode("ascii")
        data_uri = f"data:{mime};base64,{b64}"
        _company_logo_data_uri_cache[theme_id] = data_uri
        return data_uri

    _company_logo_data_uri_cache[theme_id] = ""
    return ""


def render_company_variant_svg(theme: dict, output_path: Path, logo_href: str, variant_index: int):
    theme_id = (theme.get("id") or "brand").lower()
    label = html.escape(theme.get("label", theme_id).upper()[:18])
    subtitle = html.escape(theme.get("subtitle", theme_id.title())[:24])

    palettes = [
        ("#0f172a", "#1d4ed8", "#38bdf8"),
        ("#111827", "#334155", "#14b8a6"),
        ("#0b132b", "#1e3a8a", "#60a5fa"),
        ("#1f2937", "#4f46e5", "#a78bfa"),
        ("#042f2e", "#0f766e", "#34d399"),
    ]
    logo_layouts = [
        (312, 240, 400, 400),
        (272, 300, 480, 300),
        (350, 260, 324, 324),
        (280, 248, 460, 360),
        (330, 320, 360, 260),
    ]
    p1, p2, p3 = palettes[(variant_index - 1) % len(palettes)]
    lx, ly, lw, lh = logo_layouts[(variant_index - 1) % len(logo_layouts)]
    logo_ref = html.escape(logo_href or "", quote=True)

    overlay = ""
    if variant_index % 5 == 1:
        overlay = '<circle cx="860" cy="170" r="140" fill="rgba(255,255,255,0.14)" />'
    elif variant_index % 5 == 2:
        overlay = '<rect x="70" y="90" width="300" height="180" rx="28" fill="rgba(255,255,255,0.15)" />'
    elif variant_index % 5 == 3:
        overlay = '<path d="M110 820 C340 640, 620 900, 920 700" fill="none" stroke="rgba(255,255,255,0.26)" stroke-width="12" />'
    elif variant_index % 5 == 4:
        overlay = '<circle cx="180" cy="840" r="170" fill="rgba(255,255,255,0.12)" />'
    else:
        overlay = '<rect x="710" y="80" width="240" height="240" rx="120" fill="rgba(255,255,255,0.15)" />'

    logo_layer = f'<image href="{logo_ref}" x="{lx}" y="{ly}" width="{lw}" height="{lh}" preserveAspectRatio="xMidYMid meet" />'
    if not logo_ref:
        logo_layer = (
            f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="28" fill="rgba(255,255,255,0.18)" />'
            f'<text x="{lx + 40}" y="{ly + int(lh / 2)}" fill="white" font-size="54" font-family="Arial, sans-serif" font-weight="800">{label}</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="cbg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{p1}" />
      <stop offset="60%" stop-color="{p2}" />
      <stop offset="100%" stop-color="{p3}" />
    </linearGradient>
  </defs>
  <rect width="1024" height="1024" fill="url(#cbg)" />
  {overlay}
  <rect x="76" y="74" width="320" height="54" rx="27" fill="rgba(255,255,255,0.2)" />
  <text x="102" y="110" fill="white" font-size="30" font-family="Arial, sans-serif" font-weight="700">{label}</text>
  <text x="80" y="920" fill="#e2e8f0" font-size="34" font-family="Arial, sans-serif">{subtitle}</text>
  <rect x="{lx - 24}" y="{ly - 24}" width="{lw + 48}" height="{lh + 48}" rx="34" fill="rgba(255,255,255,0.16)" />
  {logo_layer}
</svg>
"""
    output_path.write_text(svg, encoding="utf-8")


def discover_local_company_variant_images(theme_id: str, limit: int | None = None) -> list[str]:
    if not COMPANY_LOCAL_IMAGE_MODE:
        return []

    base_dir = COMPANY_IMAGE_POOL_DIR
    if not base_dir.exists():
        return []

    allowed_ext = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".ico"}
    candidates: list[Path] = []

    root_patterns = [
        f"{theme_id}-v*.*",
        f"{theme_id}_v*.*",
        f"{theme_id}-*.*",
        f"{theme_id}_*.*",
    ]
    for pattern in root_patterns:
        candidates.extend(base_dir.glob(pattern))

    nested_dir = base_dir / theme_id
    if nested_dir.exists() and nested_dir.is_dir():
        candidates.extend(nested_dir.glob("*.*"))

    unique: dict[str, Path] = {}
    for file_path in candidates:
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in allowed_ext:
            continue
        unique[str(file_path.resolve())] = file_path

    def order_key(path: Path):
        stem = path.stem.lower()
        match = re.search(r"(?:^|[-_])v?(\d+)$", stem)
        if not match:
            match = re.search(r"(?:^|[-_])v?(\d+)(?:[-_].*)?$", stem)
        seq = int(match.group(1)) if match else 10_000
        auto_bias = 1 if stem.startswith("auto-") else 0
        return (auto_bias, seq, path.name.lower())

    ordered = sorted(unique.values(), key=order_key)
    if not ordered:
        return []
    if limit is not None and limit > 0:
        ordered = ordered[:limit]
    return [to_web_path(p) for p in ordered]


def guess_extension_from_mime_or_url(content_type: str, url: str) -> str:
    ct = (content_type or "").lower()
    if "svg" in ct:
        return ".svg"
    if "png" in ct:
        return ".png"
    if "webp" in ct:
        return ".webp"
    if "gif" in ct:
        return ".gif"
    if "icon" in ct or "ico" in ct:
        return ".ico"
    if "jpeg" in ct or "jpg" in ct:
        return ".jpg"

    suffix = Path(url.split("?")[0]).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico"}:
        return suffix
    return ".jpg"


def load_company_image_hashes(image_paths: list[str]) -> set[str]:
    hashes: set[str] = set()
    for p in image_paths:
        path = Path(p)
        if not path.exists():
            continue
        try:
            hashes.add(hashlib.sha1(path.read_bytes()).hexdigest())
        except Exception:
            continue
    return hashes


def search_wikimedia_image_urls(query: str, max_urls: int) -> list[str]:
    try:
        res = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": query,
                "gsrnamespace": 6,
                "gsrlimit": min(20, max_urls),
                "prop": "imageinfo",
                "iiprop": "url|mime",
                "format": "json",
            },
            headers=REQUEST_HEADERS,
            timeout=max(4, min(8, COMPANY_SEARCH_TIMEOUT)),
        )
        if not res.ok:
            return []
        data = res.json()
    except Exception:
        return []

    pages = (data.get("query") or {}).get("pages") or {}
    urls: list[str] = []
    for page in pages.values():
        imageinfo = (page.get("imageinfo") or [{}])[0]
        url = sanitize_url(imageinfo.get("url", ""))
        if not url:
            continue
        urls.append(url)
    return urls


def build_company_search_queries(theme: dict) -> list[str]:
    company_name = (theme.get("name") or theme.get("subtitle") or theme.get("label") or theme.get("id") or "").strip()
    aliases = [a for a in theme.get("aliases", []) if a][:5]

    queries = [
        f"{company_name} logo",
        f"{company_name} company logo",
        f"{company_name} wordmark",
    ]
    for alias in aliases:
        if alias.lower() == company_name.lower():
            continue
        queries.append(f"{alias} logo")

    # Stable de-dup preserving order.
    seen: set[str] = set()
    output: list[str] = []
    for q in queries:
        norm = normalize_space(q).lower()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        output.append(q)
    return output


def build_company_candidate_urls(theme: dict, max_urls: int = 60) -> list[str]:
    urls: list[str] = []
    queries = build_company_search_queries(theme)
    company_name = (theme.get("name") or theme.get("subtitle") or theme.get("label") or theme.get("id") or "").strip()

    # Primary: Wikimedia Commons search results.
    for query in queries[:3]:
        urls.extend(search_wikimedia_image_urls(query, max_urls=12))
        if len(urls) >= max_urls:
            break

    # Secondary: direct domain logo/favicons.
    domain = (theme.get("domain") or "").strip().lower() or COMPANY_LOGO_DOMAINS.get((theme.get("id") or "").strip().lower(), "")
    if domain:
        for size in [64, 96, 128, 192, 256, 384, 512]:
            urls.append(f"https://logo.clearbit.com/{domain}?size={size}")
            urls.append(f"https://www.google.com/s2/favicons?domain_url={domain}&sz={size}")
        urls.append(f"https://icons.duckduckgo.com/ip3/{domain}.ico")

    # Tertiary: generic image search-style endpoints (not logo-only fallback).
    seed_base = int(hashlib.sha1((theme.get("id") or company_name).encode("utf-8")).hexdigest()[:8], 16) % 10_000
    for i, query in enumerate(queries[:4]):
        urls.append(f"https://source.unsplash.com/1600x900/?{quote_plus(query)}&sig={seed_base + i}")
        urls.append(f"https://loremflickr.com/1600/900/{quote_plus(query)},technology?lock={seed_base + i}")

    # Final filler: deterministic stock photos for when logo search candidates are limited.
    for i in range(1, 25):
        urls.append(f"https://picsum.photos/seed/{quote_plus((theme.get('id') or company_name) + '-' + str(i))}/1400/900")

    # Stable de-dup preserving order.
    seen: set[str] = set()
    output: list[str] = []
    for u in urls:
        cleaned = sanitize_url(u)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        output.append(cleaned)
        if len(output) >= max_urls:
            break
    return output


def store_company_candidate_image(theme_id: str, url: str, known_hashes: set[str]) -> str:
    try:
        res = requests.get(
            url,
            headers=REQUEST_HEADERS,
            timeout=max(4, min(8, COMPANY_SEARCH_TIMEOUT)),
            allow_redirects=True,
        )
    except Exception:
        return ""

    if not res.ok:
        return ""
    content_type = (res.headers.get("content-type") or "").lower()
    if "image/" not in content_type:
        return ""

    payload = res.content or b""
    if len(payload) < 80:
        return ""

    digest = hashlib.sha1(payload).hexdigest()
    if digest in known_hashes:
        return ""

    ext = guess_extension_from_mime_or_url(content_type=content_type, url=url)
    out_dir = COMPANY_IMAGE_POOL_DIR / theme_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"auto-{digest[:14]}{ext}"
    if not out_path.exists():
        try:
            out_path.write_bytes(payload)
        except Exception:
            return ""

    known_hashes.add(digest)
    return to_web_path(out_path)


def populate_company_image_pool(theme: dict, target_count: int) -> int:
    theme_id = (theme.get("id") or "").strip().lower()
    if not theme_id:
        return 0

    existing_paths = discover_local_company_variant_images(theme_id, limit=None)
    known_hashes = load_company_image_hashes(existing_paths)
    current_count = len(existing_paths)
    if current_count >= target_count:
        return 0

    added = 0
    missing = max(0, target_count - current_count)
    max_attempts = max(18, min(60, missing * 8))
    attempts = 0

    for candidate_url in build_company_candidate_urls(theme, max_urls=max_attempts):
        attempts += 1
        if attempts > max_attempts:
            break
        if current_count + added >= target_count:
            break
        saved = store_company_candidate_image(theme_id=theme_id, url=candidate_url, known_hashes=known_hashes)
        if not saved:
            continue
        added += 1
    return added


def ensure_company_variant_images(theme: dict) -> list[str]:
    theme_id = (theme.get("id") or "").strip().lower()
    if not theme_id:
        return []

    cached = _company_variant_paths_cache.get(theme_id, [])
    if cached and all(Path(p).exists() for p in cached):
        return cached

    local_paths = discover_local_company_variant_images(theme_id, limit=None)
    added_from_search = 0
    if COMPANY_SEARCH_IMAGE_ENABLED and len(local_paths) < COMPANY_SEARCH_IMAGE_TARGET:
        added_from_search = populate_company_image_pool(theme=theme, target_count=COMPANY_SEARCH_IMAGE_TARGET)
        if added_from_search > 0:
            local_paths = discover_local_company_variant_images(theme_id, limit=None)

    if local_paths:
        _company_variant_paths_cache[theme_id] = local_paths
        if added_from_search > 0 or any(Path(p).name.startswith("auto-") for p in local_paths):
            _company_variant_source_cache[theme_id] = "searched-pool"
        else:
            _company_variant_source_cache[theme_id] = "local-pool"
        return local_paths

    asset_dir = IMAGE_OUTPUT_DIR / "company_variants"
    asset_dir.mkdir(parents=True, exist_ok=True)

    logo_href = fetch_company_logo_data_uri(theme) or get_company_logo_url(theme)
    if not logo_href:
        _company_variant_source_cache[theme_id] = "none"
        return []

    paths: list[str] = []
    for i in range(1, COMPANY_VARIANT_COUNT + 1):
        path = asset_dir / f"{theme_id}-v{i}.svg"
        if not path.exists():
            render_company_variant_svg(theme=theme, output_path=path, logo_href=logo_href, variant_index=i)
        paths.append(to_web_path(path))

    _company_variant_paths_cache[theme_id] = paths
    _company_variant_source_cache[theme_id] = "generated-logo-variants"
    return paths


def pick_company_variant_image(theme: dict, article_uid: str = "", title: str = "") -> tuple[str, int, str]:
    paths = ensure_company_variant_images(theme)
    if not paths:
        return "", -1, "none"

    theme_id = (theme.get("id") or "").strip().lower()
    if COMPANY_DAILY_ROTATION:
        day_key = datetime.now().strftime("%Y-%m-%d")
        uid = article_uid or title or day_key
        seed = hashlib.sha1(f"{theme_id}|{day_key}|{uid}".encode("utf-8")).hexdigest()
        picked = int(seed[:12], 16) % len(paths)
    else:
        last_idx = _company_last_variant_index.get(theme_id, -1)
        candidates = list(range(len(paths)))
        if len(candidates) > 1 and last_idx in candidates:
            candidates.remove(last_idx)
        picked = random.SystemRandom().choice(candidates)
        _company_last_variant_index[theme_id] = picked

    source = _company_variant_source_cache.get(theme_id, "generated-logo-variants")
    return paths[picked], picked + 1, source


def find_keyword_theme(text: str):
    text_lower = (text or "").lower()
    best_match = None

    def scan(themes: list[dict], priority: int):
        nonlocal best_match
        for theme in themes:
            for keyword in theme.get("keywords", []):
                needle = keyword.lower().strip()
                if not needle:
                    continue
                pos = text_lower.find(needle)
                if pos < 0:
                    continue
                # Lower tuple wins: company priority -> earlier mention -> longer keyword.
                score = (priority, pos, -len(needle))
                if best_match is None or score < best_match[0]:
                    best_match = (score, theme, keyword)

    scan(COMPANY_THEMES, priority=0)
    scan(KEYWORD_THEMES, priority=1)
    if not best_match:
        return None, ""
    return best_match[1], best_match[2]


def build_representative_queries(theme: dict, matched_keyword: str) -> list[str]:
    queries: list[str] = []
    theme_id = (theme.get("id") or "").lower()

    for query in theme.get("search_queries", []) or []:
        q = normalize_space(query)
        if q:
            queries.append(q)

    for query in KEYWORD_THEME_SEARCH_QUERIES.get(theme_id, []):
        q = normalize_space(query)
        if q:
            queries.append(q)

    keyword_clean = normalize_space(matched_keyword)
    if keyword_clean:
        queries.insert(0, f"{keyword_clean} technology")
        queries.insert(0, keyword_clean)

    # Stable de-dup preserving order.
    ordered_unique: list[str] = []
    seen: set[str] = set()
    for q in queries:
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered_unique.append(q)

    return ordered_unique


def build_keyword_photo_prompt(theme: dict, matched_keyword: str, title: str) -> str:
    subject_map = {
        "ai": "an engineer working with AI interface holograms",
        "security": "a cybersecurity analyst monitoring threat dashboards",
        "semiconductor": "a close-up semiconductor wafer and chip lab",
        "mobile": "a modern smartphone in natural light on a desk",
        "cloud": "server racks in a clean cloud datacenter",
        "robotics": "a humanoid robot in an industrial workspace",
        "gaming": "a gaming setup with controller and display",
        "space": "a satellite and earth horizon in realistic style",
    }
    subject = theme.get("prompt_subject") or subject_map.get(theme.get("id", ""), "a modern technology workplace")
    return (
        f"Photorealistic editorial photo, {subject}, topic: {title}, "
        f"keyword: {matched_keyword}, simple composition, natural lighting, "
        "high detail, no text, no logo, no watermark"
    )


def download_stock_photo_for_keyword(
    theme: dict,
    matched_keyword: str,
    article_uid: str,
    output_path: Path,
) -> bool:
    if not KEYWORD_STOCK_ENABLED:
        return False

    uid_source = article_uid or f"{theme.get('id','tech')}|{matched_keyword}"
    uid_hash = hashlib.sha1(uid_source.encode("utf-8")).hexdigest()
    lock_num = int(uid_hash[:8], 16) % 1_000_000 + 1

    default_theme_tags = {
        "ai": "technology,computer,data",
        "security": "technology,computer,code",
        "semiconductor": "technology,electronics,circuit",
        "mobile": "smartphone,technology,device",
        "cloud": "server,technology,datacenter",
        "robotics": "robot,technology,industry",
        "gaming": "gaming,computer,technology",
        "space": "space,technology,satellite",
    }
    theme_id = (theme.get("id") or "technology").lower()
    theme_tag_pool = list(theme.get("stock_tags") or [])
    if not theme_tag_pool:
        theme_tag_pool = [default_theme_tags.get(theme_id, "technology,computer")]

    start_index = int(uid_hash[8:12], 16) % len(theme_tag_pool)
    ordered_tags = [theme_tag_pool[(start_index + i) % len(theme_tag_pool)] for i in range(len(theme_tag_pool))]

    query_pool = build_representative_queries(theme=theme, matched_keyword=matched_keyword)
    if not query_pool:
        query_pool = [f"{theme_id} technology"]
    query_start = int(uid_hash[12:16], 16) % len(query_pool)
    ordered_queries = [query_pool[(query_start + i) % len(query_pool)] for i in range(len(query_pool))]

    url_pool: list[str] = []
    if KEYWORD_REPRESENTATIVE_QUERY_ENABLED:
        sig_base = int(uid_hash[:8], 16) % 10_000
        for i, query in enumerate(ordered_queries[:6]):
            url_pool.append(f"https://source.unsplash.com/1600x900/?{quote_plus(query)}&sig={sig_base + i}")

    keyword_ascii = re.sub(r"[^a-z0-9]+", ",", (matched_keyword or "").lower()).strip(",")
    if keyword_ascii:
        url_pool.append(f"https://loremflickr.com/1600/900/{quote_plus(keyword_ascii)},technology?lock={lock_num}")

    url_pool.extend(
        f"https://loremflickr.com/1600/900/{tags}?lock={lock_num + i}"
        for i, tags in enumerate(ordered_tags[:4])
    )

    # Final fallback: deterministic real photo (not keyword-perfect, but still photographic).
    seed = quote_plus(f"{theme_id}-{matched_keyword or 'tech'}-{uid_hash[:10]}")
    url_pool.append(f"https://picsum.photos/seed/{seed}/1600/900")

    for stock_url in url_pool:
        payload = fetch_image_payload(stock_url, KEYWORD_STOCK_TIMEOUT)
        if not payload:
            continue
        if not claim_image_bytes_for_run(payload):
            continue
        output_path.write_bytes(payload)
        return True

    return False


def render_keyword_svg_cover(
    title: str,
    source: str,
    theme: dict,
    matched_keyword: str,
    output_path: Path,
):
    c1, c2, c3 = theme["colors"]
    label = html.escape(theme["label"][:20])
    subtitle = html.escape(theme["subtitle"][:36])
    safe_source = html.escape(source[:20] or "Tech News")
    safe_title = html.escape(title[:52] + ("..." if len(title) > 52 else ""))
    key_text = html.escape(matched_keyword[:24])

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="kwbg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{c1}" />
      <stop offset="60%" stop-color="{c2}" />
      <stop offset="100%" stop-color="{c3}" />
    </linearGradient>
  </defs>
  <rect width="1024" height="1024" fill="url(#kwbg)" />
  <g opacity="0.16" fill="none" stroke="white" stroke-width="3">
    <circle cx="860" cy="200" r="140" />
    <circle cx="180" cy="860" r="180" />
    <path d="M140 700 C360 520, 640 860, 900 650" />
  </g>
  <rect x="72" y="72" width="250" height="46" rx="23" fill="rgba(255,255,255,0.18)" />
  <text x="94" y="103" fill="white" font-size="24" font-family="Arial, sans-serif" font-weight="700">{safe_source}</text>
  <rect x="76" y="136" width="220" height="38" rx="19" fill="rgba(255,255,255,0.12)" />
  <text x="94" y="162" fill="#e2e8f0" font-size="20" font-family="Arial, sans-serif">{key_text}</text>
  <text x="80" y="560" fill="white" font-size="112" font-family="Arial, sans-serif" font-weight="800">{label}</text>
  <text x="82" y="610" fill="#dbeafe" font-size="32" font-family="Arial, sans-serif">{subtitle}</text>
  <text x="80" y="892" fill="#f8fafc" font-size="34" font-family="Arial, sans-serif">{safe_title}</text>
</svg>
"""
    output_path.write_text(svg, encoding="utf-8")


def download_generic_stock_photo(title: str, source: str, article_uid: str, output_path: Path) -> bool:
    if not KEYWORD_STOCK_ENABLED:
        return False

    uid_source = article_uid or f"{source}|{title}"
    uid_hash = hashlib.sha1(uid_source.encode("utf-8")).hexdigest()
    lock_num = int(uid_hash[:8], 16) % 1_000_000 + 1

    ascii_terms = re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", f"{title} {source}".lower())
    noisy = {"the", "and", "for", "with", "from", "news", "tech", "today"}
    token = next((x for x in ascii_terms if x not in noisy), "technology")

    query_pool = [
        f"{token} technology",
        f"{source} technology",
        "technology startup office",
        "computer innovation workspace",
    ]
    # Stable de-dup preserving order.
    ordered_unique_queries: list[str] = []
    seen_queries: set[str] = set()
    for query in query_pool:
        q = normalize_space(query).lower()
        if not q or q in seen_queries:
            continue
        seen_queries.add(q)
        ordered_unique_queries.append(query)

    url_pool: list[str] = []
    if KEYWORD_REPRESENTATIVE_QUERY_ENABLED and ordered_unique_queries:
        query_start = int(uid_hash[12:16], 16) % len(ordered_unique_queries)
        sig_base = int(uid_hash[:8], 16) % 10_000
        ordered_queries = [
            ordered_unique_queries[(query_start + i) % len(ordered_unique_queries)]
            for i in range(len(ordered_unique_queries))
        ]
        for i, query in enumerate(ordered_queries[:4]):
            url_pool.append(f"https://source.unsplash.com/1600x900/?{quote_plus(query)}&sig={sig_base + i}")

    url_pool.extend(
        [
            f"https://loremflickr.com/1600/900/technology,computer?lock={lock_num}",
            f"https://loremflickr.com/1600/900/{quote_plus(token)},technology?lock={lock_num + 1}",
            f"https://picsum.photos/seed/{quote_plus(uid_hash[:16])}/1600/900",
        ]
    )

    for stock_url in url_pool:
        payload = fetch_image_payload(stock_url, KEYWORD_STOCK_TIMEOUT)
        if not payload:
            continue
        if not claim_image_bytes_for_run(payload):
            continue
        output_path.write_bytes(payload)
        return True

    return False


def build_fallback_prompt(title: str, source: str) -> str:
    return (
        f"{NEWS_IMAGE_STYLE}. Topic: {title}. Source context: {source}. "
        "Editorial cover style."
    )


def build_fallback_summary(title: str, original_content: str) -> str:
    text = clean_summary(original_content) or title
    text = normalize_space(text)
    if len(text) > 240:
        return text[:240].rstrip() + "..."
    return text


def parse_json_from_response_text(text: str) -> dict:
    if not text:
        return {}
    raw = text.strip()

    # Prefer fenced JSON if model returned markdown.
    fenced = re.search(r"```(?:json)?\s*({[\s\S]*?})\s*```", raw, re.IGNORECASE)
    if fenced:
        raw = fenced.group(1).strip()
    else:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start : end + 1]

    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def get_latest_gemini_model() -> str:
    """사용 가능한 최신 Gemini 3 flash 계열 모델명을 탐색합니다."""
    fallback = "gemini-1.5-flash"
    if genai is None or not GEMINI_API_KEY:
        return fallback

    try:
        matched: list[str] = []
        for m in genai.list_models():
            methods = getattr(m, "supported_generation_methods", []) or []
            if "generateContent" not in methods:
                continue
            name = getattr(m, "name", "") or ""
            if "gemini-3-flash" in name:
                matched.append(name)
        if matched:
            return sorted(matched)[-1]
    except Exception as e:
        print(f"[WARN] Failed to list Gemini models: {e}")

    return fallback


def get_gemini_text_model():
    global _gemini_text_model_name
    global _gemini_text_model

    if genai is None or not GEMINI_API_KEY:
        return None
    if _gemini_text_model is not None:
        return _gemini_text_model

    model_name = os.getenv("GEMINI_CURATION_MODEL", "").strip() or get_latest_gemini_model()
    try:
        _gemini_text_model = genai.GenerativeModel(model_name)
        _gemini_text_model_name = model_name
        return _gemini_text_model
    except Exception as e:
        print(f"[WARN] Failed to initialize Gemini model {model_name}: {e}")
        return None


def recreate_news_content(title: str, original_content: str, source: str) -> dict:
    """
    뉴스 요약 재창작 + 이미지 프롬프트를 동시에 생성합니다.
    Returns: {"summary": str, "image_prompt": str, "model": str, "mode": str}
    """
    global _curation_count

    fallback_summary = build_fallback_summary(title, original_content)
    fallback_prompt = build_fallback_prompt(title, source)

    if not NEWS_CURATION_ENABLED:
        return {
            "summary": fallback_summary,
            "image_prompt": fallback_prompt,
            "model": "",
            "mode": "curation-disabled",
        }

    if NEWS_CURATION_LIMIT > 0 and _curation_count >= NEWS_CURATION_LIMIT:
        return {
            "summary": fallback_summary,
            "image_prompt": fallback_prompt,
            "model": "",
            "mode": "curation-limit-reached",
        }

    model = get_gemini_text_model()
    if model is None:
        return {
            "summary": fallback_summary,
            "image_prompt": fallback_prompt,
            "model": "",
            "mode": "curation-fallback",
        }

    prompt = f"""
당신은 IT/AI/로봇 전문 콘텐츠 에디터입니다.
제공된 뉴스 정보를 바탕으로 아래 두 항목을 생성하세요.

1) curated_summary
- 원문 문장을 그대로 복사하지 말고, 완전히 재창작한 한국어 요약 2~3문장
- 비전공자도 이해 가능한 쉬운 표현

2) image_prompt
- 기사 원문 사진을 대체할 수 있는 미래지향적 3D 렌더링 스타일의 영어 프롬프트 1개
- 로고/워터마크/텍스트 오버레이 금지

반드시 JSON만 반환:
{{
  "curated_summary": "...",
  "image_prompt": "..."
}}

[뉴스 정보]
출처: {source}
제목: {title}
원문 내용: {original_content}
"""

    try:
        response = model.generate_content(prompt)
        payload = parse_json_from_response_text(getattr(response, "text", ""))

        curated_summary = normalize_space(payload.get("curated_summary", ""))
        image_prompt = normalize_space(payload.get("image_prompt", ""))
        if not curated_summary:
            curated_summary = fallback_summary
        if not image_prompt:
            image_prompt = fallback_prompt

        _curation_count += 1
        return {
            "summary": curated_summary,
            "image_prompt": image_prompt,
            "model": _gemini_text_model_name,
            "mode": "curation-success",
        }
    except Exception as e:
        print(f"[WARN] recreate_news_content failed: {e}")
        return {
            "summary": fallback_summary,
            "image_prompt": fallback_prompt,
            "model": _gemini_text_model_name,
            "mode": "curation-error",
        }


def extract_text_from_gemini_response(data: dict) -> str:
    for candidate in data.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            text = part.get("text")
            if text:
                return text.strip()
    return ""


def generate_prompt_with_gemini(title: str, source: str) -> str:
    fallback = build_fallback_prompt(title, source)
    if not GEMINI_API_KEY:
        return fallback

    try:
        prompt_task = (
            "You are a prompt writer for editorial tech cover images.\n"
            "Return exactly one English prompt only.\n"
            f"News title: {title}\n"
            f"Source: {source}\n"
            f"Style constraints: {NEWS_IMAGE_STYLE}\n"
            "The prompt must request one clean 3D illustration with no logos or text."
        )

        res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_PROMPT_MODEL}:generateContent",
            headers={"Content-Type": "application/json"},
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt_task}]}]},
            timeout=25,
        )
        if not res.ok:
            print(f"[WARN] Gemini prompt generation failed: {res.status_code}")
            return fallback

        prompt = extract_text_from_gemini_response(res.json())
        return prompt or fallback
    except Exception as e:
        print(f"[WARN] Gemini prompt generation error: {e}")
        return fallback


def generate_image_with_gemini(prompt: str, output_path: Path) -> bool:
    if not GEMINI_API_KEY:
        return False

    try:
        res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_IMAGE_MODEL}:generateContent",
            headers={"Content-Type": "application/json"},
            params={"key": GEMINI_API_KEY},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["Image", "Text"]},
            },
            timeout=90,
        )
        if not res.ok:
            print(f"[WARN] Gemini image generation failed: {res.status_code}")
            return False

        data = res.json()
        for candidate in data.get("candidates", []):
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                inline = part.get("inlineData") or {}
                b64 = inline.get("data")
                mime = inline.get("mimeType", "")
                if b64 and mime.startswith("image/"):
                    output_path.write_bytes(base64.b64decode(b64))
                    return True

        return False
    except Exception as e:
        print(f"[WARN] Gemini image generation error: {e}")
        return False


def render_local_svg_cover(title: str, source: str, output_path: Path, theme_id: str = ""):
    palette_by_theme = {
        "ai": ("#0b1020", "#1d4ed8", "#22d3ee"),
        "security": ("#111827", "#1f2937", "#0ea5e9"),
        "semiconductor": ("#1f1b4b", "#4338ca", "#a78bfa"),
        "mobile": ("#082f49", "#0369a1", "#67e8f9"),
        "cloud": ("#0f172a", "#334155", "#38bdf8"),
        "robotics": ("#052e2b", "#0f766e", "#2dd4bf"),
        "gaming": ("#1f1147", "#6d28d9", "#a78bfa"),
        "space": ("#0b1020", "#1e3a8a", "#60a5fa"),
        "general": ("#0f172a", "#1e40af", "#38bdf8"),
    }
    base_palette = palette_by_theme.get((theme_id or "").lower(), palette_by_theme["general"])
    # Keep per-article variety while staying in the selected theme palette.
    hue_shift = int(hashlib.sha1(title.encode("utf-8")).hexdigest(), 16) % 2
    if hue_shift == 0:
        p1, p2, p3 = base_palette
    else:
        p1, p2, p3 = (base_palette[1], base_palette[2], base_palette[0])

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{p1}" />
      <stop offset="60%" stop-color="{p2}" />
      <stop offset="100%" stop-color="{p3}" />
    </linearGradient>
    <radialGradient id="glow" cx="0.8" cy="0.2" r="0.7">
      <stop offset="0%" stop-color="rgba(255,255,255,0.25)" />
      <stop offset="100%" stop-color="rgba(255,255,255,0)" />
    </radialGradient>
  </defs>
  <rect width="1024" height="1024" fill="url(#bg)" />
  <rect width="1024" height="1024" fill="url(#glow)" />
  <g opacity="0.17" stroke="white" stroke-width="2" fill="none">
    <circle cx="210" cy="180" r="120" />
    <circle cx="860" cy="760" r="180" />
    <path d="M120 800 C360 640, 620 900, 910 700" />
  </g>
  <g opacity="0.28" fill="none" stroke="#ffffff" stroke-width="8">
    <rect x="300" y="260" width="420" height="300" rx="36" />
    <circle cx="510" cy="410" r="76" />
    <path d="M342 520 L460 430 L545 500 L678 360" />
  </g>
</svg>
"""
    output_path.write_text(svg, encoding="utf-8")


def generate_reference_image(
    title: str,
    source: str,
    prompt_override: str = "",
    article_uid: str = "",
    context_text: str = "",
):
    uid = article_uid or f"{source}|{title}"
    digest = hashlib.sha1(f"{source}|{title}|{uid}".encode("utf-8")).hexdigest()[:12]
    stem = f"{slugify(title)}-{digest}"
    company_theme, company_keyword = find_company_theme_in_title(title)
    if COMPANY_LOGO_PRIORITY_MODE and company_theme:
        variant_image, variant_no, variant_source = pick_company_variant_image(
            company_theme, article_uid=uid, title=title
        )
        if variant_image:
            if variant_source == "local-pool":
                prompt = f"company-local-pool:{company_theme.get('id')}:{company_keyword}:v{variant_no}"
                return variant_image, prompt, "company-local-image-pool"
            if variant_source == "searched-pool":
                prompt = f"company-searched-pool:{company_theme.get('id')}:{company_keyword}:v{variant_no}"
                return variant_image, prompt, "company-searched-image-pool"
            prompt = f"company-logo-variant:{company_theme.get('id')}:{company_keyword}:v{variant_no}"
            return variant_image, prompt, "company-logo-variant"

        logo_url = get_company_logo_url(company_theme)
        if logo_url:
            prompt = f"company-logo:{company_theme.get('id')}:{company_keyword}"
            return logo_url, prompt, "company-logo"

    search_text = f"{title} {context_text}".strip()
    theme, matched_keyword = find_keyword_theme(search_text)
    theme_id = (theme or {}).get("id", "general")

    simple_svg_path = IMAGE_OUTPUT_DIR / f"{stem}-simple.svg"
    if not simple_svg_path.exists():
        render_local_svg_cover(
            title=f"{theme_id}|{title}",
            source=source,
            output_path=simple_svg_path,
            theme_id=theme_id,
        )

    prompt = f"simple-illustration:{theme_id}:{matched_keyword or 'none'}"
    return to_web_path(simple_svg_path), prompt, "simple-illustration"


def make_record(
    *,
    country_ko: str,
    country_en: str,
    media: str,
    title: str,
    link: str,
    summary: str,
    image: str,
    collected_at: str,
    image_prompt: str,
    image_provider: str,
    curation_model: str = "",
    curation_mode: str = "",
) -> dict:
    return {
        KEY_COUNTRY: country_ko,
        KEY_MEDIA: media,
        KEY_TITLE: title,
        KEY_LINK: link,
        KEY_SUMMARY: summary,
        KEY_IMAGE: image,
        KEY_COLLECTED_AT: collected_at,
        KEY_IMAGE_PROMPT: image_prompt,
        KEY_IMAGE_PROVIDER: image_provider,
        "country": country_en,
        "media": media,
        "title": title,
        "link": link,
        "summary": summary,
        "image": image,
        "collected_at": collected_at,
        "image_prompt": image_prompt,
        "image_provider": image_provider,
        "curation_model": curation_model,
        "curation_mode": curation_mode,
    }


def collect_domestic_news(now: str) -> list[dict]:
    items_out: list[dict] = []
    print("Collecting Domestic News from: Naver IT/Science Section")

    list_url = "https://news.naver.com/section/105"
    r = requests.get(list_url, headers=REQUEST_HEADERS, timeout=8)
    if r.status_code != 200:
        print(f"[WARN] Failed to fetch Naver IT news list page: {r.status_code}")
        return items_out

    soup = BeautifulSoup(r.text, "html.parser")
    # Change selector to capture the whole item which includes both thumb and text
    news_items = soup.select(".sa_item_inner")[:10]
    print(f"Found {len(news_items)} domestic news items")

    for idx, item in enumerate(news_items, start=1):
        text_area = item.select_one(".sa_text")
        if not text_area:
            continue
            
        link_elem = text_area.select_one("a[href]")
        if not link_elem:
            continue

        title = link_elem.get_text(strip=True)
        link = link_elem.get("href", "").strip()
        if link and not link.startswith("http"):
            link = urljoin("https://news.naver.com", link)

        # Extract Thumbnail if available
        image_url = ""
        thumb_area = item.select_one(".sa_thumb")
        if thumb_area:
            img_tag = thumb_area.select_one("img")
            if img_tag:
                image_url = img_tag.get("src") or img_tag.get("data-src") or ""
                # Naver thumbnails sometimes have query params for resizing, we can use them as is or strip them.
                # Usually standard extraction is fine.
        
        media_name = VAL_NAVER_NEWS
        media_elem = text_area.select_one(".sa_text_press")
        if media_elem:
            media_name = media_elem.get_text(strip=True) or media_name

        summary_elem = text_area.select_one(".sa_text_lede")
        original_content = summary_elem.get_text(strip=True) if summary_elem else title
        curation = recreate_news_content(title=title, original_content=original_content, source=media_name)
        summary = curation["summary"]
        image_prompt = curation["image_prompt"]

        # Image Assignment Logic
        final_image = ""
        provider = ""
        prompt = ""

        # Priority 1: Use extracted source image if available
        if image_url:
             final_image = image_url
             provider = "source-original"
             prompt = "original-source-image"
        else:
            # Fallback to existing generation logic
            gen_image, gen_prompt, gen_provider = generate_reference_image(
                title=title,
                source=media_name,
                prompt_override=image_prompt,
                article_uid=link,
                context_text=original_content,
            )
            final_image = gen_image
            prompt = gen_prompt
            provider = gen_provider

        preview = safe_console_text(title[:40])
        print(f"  {idx}. {preview}... [{provider}]")

        items_out.append(
            make_record(
                country_ko=VAL_DOMESTIC,
                country_en="domestic",
                media=media_name,
                title=title,
                link=link,
                summary=summary,
                image=final_image,
                collected_at=now,
                image_prompt=prompt,
                image_provider=provider,
                curation_model=curation.get("model", ""),
                curation_mode=curation.get("mode", ""),
            )
        )

    return items_out


    return items_out


def collect_hacker_news(now: str) -> list[dict]:
    items_out: list[dict] = []
    print("Collecting Global News from: Hacker News (API)")
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        top_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        r = requests.get(top_url, headers=headers, timeout=5)
        if r.status_code != 200:
            return []
        
        story_ids = r.json()[:10]  # Top 10
        
        for sid in story_ids:
            item_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
            ir = requests.get(item_url, headers=headers, timeout=3)
            if ir.status_code != 200:
                continue
                
            item = ir.json()
            if not item or item.get('type') != 'story':
                continue

            title = item.get('title', '')
            link = item.get('url', '')
            score = item.get('score', 0)
            descendants = item.get('descendants', 0)
            by = item.get('by', '')
            
            summary = f"Points: {score} | Comments: {descendants} | By: {by}"
            
            # Hacker News는 이미지가 없으므로 Fallback 로직 활용
            image_url, prompt, provider = generate_reference_image(
                title=title,
                source="Hacker News",
                article_uid=str(sid),
                context_text=title
            )
            
            if not link:
                link = f"https://news.ycombinator.com/item?id={sid}"

            items_out.append(
                make_record(
                    country_ko=VAL_US,
                    country_en="global",
                    media="Hacker News",
                    title=title,
                    link=link,
                    summary=summary,
                    image=image_url,
                    collected_at=now,
                    image_prompt=prompt,
                    image_provider=provider,
                    curation_model="",
                    curation_mode="api-metadata"
                )
            )
            time.sleep(0.1)

    except Exception as e:
        print(f"[WARN] Failed to collect Hacker News: {e}")
        
    return items_out


def collect_global_news(now: str) -> list[dict]:
    items_out: list[dict] = []
    usa_feeds = {
        "TechCrunch": "https://techcrunch.com/feed/",
        "The Verge": "https://www.theverge.com/rss/index.xml",
        "Wired": "https://www.wired.com/feed/rss",
        "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
        # New Tech Blogs
        "OpenAI Blog": "https://openai.com/news/rss.xml",
        "Google DeepMind": "https://deepmind.google/blog/rss.xml",
        "Google Research": "https://research.google/blog/rss",
        "Microsoft Research": "https://www.microsoft.com/en-us/research/feed/",
    }

    for source, url in usa_feeds.items():
        try:
            print(f"Collecting Global News from: {source}")
            parsed = parse_rss_feed(url, max_items=8)
            feed_items = parsed.get("items", [])
            feed_meta = parsed.get("meta", {})
            feed_allow = feed_explicitly_allows_rss_images(feed_meta)

            source_key = source.strip().lower()
            if source_key in RSS_IMAGE_FORCE_ALLOW_SOURCES:
                policy_note = "force-allow"
            elif source_key in RSS_IMAGE_FORCE_DENY_SOURCES:
                policy_note = "force-deny"
            else:
                policy_note = "explicit-allow" if feed_allow else "no-explicit-allow"
            print(f"  - RSS image policy: {policy_note}")

            for item in feed_items:
                title = item.get("title", "")
                link = item.get("link", "")
                original_content = item.get("description", "")
                curation = recreate_news_content(title=title, original_content=original_content, source=source)
                summary = curation["summary"]
                image_prompt = curation["image_prompt"]
                rss_image_url = item.get("rss_image_url", "")
                item_rights = item.get("item_rights", "")

                if USE_RSS_SOURCE_IMAGE and should_use_rss_source_image(
                    source_name=source,
                    rss_image_url=rss_image_url,
                    feed_allows=feed_allow,
                    item_rights=item_rights,
                ) and claim_remote_image_url_for_run(rss_image_url):
                    image_url = rss_image_url
                    prompt = "rss-image-direct-use"
                    provider = "rss-source-image"
                else:
                    image_url, prompt, provider = generate_reference_image(
                        title=title,
                        source=source,
                        prompt_override=image_prompt,
                        article_uid=link,
                        context_text=original_content,
                    )

                items_out.append(
                    make_record(
                        country_ko=VAL_US,
                        country_en="global",
                        media=source,
                        title=title,
                        link=link,
                        summary=summary,
                        image=image_url,
                        collected_at=now,
                        image_prompt=prompt,
                        image_provider=provider,
                        curation_model=curation.get("model", ""),
                        curation_mode=curation.get("mode", ""),
                    )
                )
        except Exception as e:
            print(f"[WARN] Failed to collect {source}: {e}")

    return items_out


def collect_news() -> list[dict]:
    global _used_image_hashes_in_run
    global _used_remote_image_urls_in_run
    global _company_logo_data_uri_cache
    global _company_variant_paths_cache
    global _company_variant_source_cache
    global _company_last_variant_index

    _used_image_hashes_in_run.clear()
    _used_remote_image_urls_in_run.clear()
    _company_logo_data_uri_cache.clear()
    _company_variant_paths_cache.clear()
    _company_variant_source_cache.clear()
    _company_last_variant_index.clear()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    COMPANY_IMAGE_POOL_DIR.mkdir(parents=True, exist_ok=True)

    if not GEMINI_API_KEY:
        print("[INFO] GEMINI_API_KEY not found. Local SVG covers will be generated.")
    else:
        print(f"[INFO] GEMINI_API_KEY detected. AI image cap: {NEWS_AI_IMAGE_LIMIT}")
        if NEWS_CURATION_ENABLED:
            suggested = os.getenv("GEMINI_CURATION_MODEL", "").strip() or get_latest_gemini_model()
            print(
                f"[INFO] Curation enabled. model={suggested}, "
                f"limit={NEWS_CURATION_LIMIT if NEWS_CURATION_LIMIT else 'unlimited'}"
            )
        else:
            print("[INFO] Curation disabled. Using source summary/fallback prompt.")

    all_news: list[dict] = []

    try:
        all_news.extend(collect_domestic_news(now))
    except Exception as e:
        print(f"[WARN] Failed to collect Domestic news: {e}")

    all_news.extend(collect_global_news(now))
    
    # Hacker News 추가
    all_news.extend(collect_hacker_news(now))

    # -------------------------------------------------------------------------
    # Sorting & Prioritization
    # - OpenAI 관련 뉴스를 최상단으로 올립니다.
    # -------------------------------------------------------------------------
    def sort_key(item):
        # OpenAI 키워드가 제목이나 매체에 있으면 우선순위 0 (가장 높음)
        # 그 외에는 1
        title_lower = (item.get(KEY_TITLE) or "").lower()
        media_lower = (item.get(KEY_MEDIA) or "").lower()
        
        if 'openai' in title_lower or 'openai' in media_lower:
            return 0
        return 1

    # Python의 sort는 stable하므로, 기존 순서(최신순/소스순)를 유지하면서 그룹핑됩니다.
    all_news.sort(key=sort_key)

    return all_news


def main():
    json_name = "news_data.json"
    existing_items = []
    if Path(json_name).exists():
        try:
            with open(json_name, "r", encoding="utf-8") as f:
                existing_items = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load existing {json_name}: {e}")

    # Retain items collected within the last 7 days
    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)
    
    retained_items = []
    for item in existing_items:
        collected_at_str = item.get("collected_at") or item.get("수집일시")
        if collected_at_str:
            try:
                # Format is usually "%Y-%m-%d %H:%M"
                item_date = datetime.strptime(collected_at_str, "%Y-%m-%d %H:%M")
                if item_date >= seven_days_ago:
                    retained_items.append(item)
            except ValueError:
                # If date format is weird, just keep it for now
                retained_items.append(item)

    print(f"[INFO] Retained {len(retained_items)} items from the last 7 days.")

    new_items = collect_news()
    
    # Combine and Deduplicate by link or title
    seen_links = set()
    combined_items = []
    
    # Add new items first to ensure they take precedence
    for item in new_items:
        link = item.get("link") or item.get("링크")
        title = item.get("title") or item.get("제목")
        dedup_key = link if link else title
        if dedup_key not in seen_links:
            seen_links.add(dedup_key)
            combined_items.append(item)

    # Add retained older items second
    for item in retained_items:
        link = item.get("link") or item.get("링크")
        title = item.get("title") or item.get("제목")
        dedup_key = link if link else title
        if dedup_key not in seen_links:
            seen_links.add(dedup_key)
            combined_items.append(item)

    # Sort combined items (OpenAI priorities, then latest first)
    def sort_key(item):
        title_lower = (item.get("title") or item.get("제목") or "").lower()
        media_lower = (item.get("media") or item.get("매체") or "").lower()
        collected_at = item.get("collected_at") or item.get("수집일시") or ""
        
        is_prioritized = 0 if ('openai' in title_lower or 'openai' in media_lower) else 1
        # Secondary sort by date descending
        return (is_prioritized, collected_at)

    combined_items.sort(key=sort_key, reverse=True) # Sort reverse=True so newest is first in each priority group
    # However we need priority 0 (is_prioritized=0) to be at the top. Since reverse=True, 0 will go to the bottom if we aren't careful.
    # So let's invert the boolean or priority number.
    
    def final_sort_key(item):
        title_lower = (item.get("title") or item.get("제목") or "").lower()
        media_lower = (item.get("media") or item.get("매체") or "").lower()
        collected_at = item.get("collected_at") or item.get("수집일시") or ""
        
        # Lower number is better priority.
        priority = 0 if ('openai' in title_lower or 'openai' in media_lower) else 1
        return (priority, collected_at)

    # To sort by priority ASC, date DESC:
    combined_items.sort(key=lambda x: x.get("collected_at") or x.get("수집일시") or "", reverse=True)
    combined_items.sort(key=lambda x: 0 if 'openai' in (x.get("title") or x.get("제목") or "").lower() or 'openai' in (x.get("media") or x.get("매체") or "").lower() else 1)

    with open(json_name, "w", encoding="utf-8") as f:
        json.dump(combined_items, f, ensure_ascii=False, indent=2)

    domestic_count = sum(1 for item in combined_items if (item.get("국가") == "국내" or item.get("country") == "domestic"))
    us_count = sum(1 for item in combined_items if (item.get("국가") == "미국" or item.get("country") == "global"))

    print(f"[OK] Wrote {len(combined_items)} items to {json_name}")
    print(f"- Domestic: {domestic_count}")
    print(f"- US/Global: {us_count}")

    # Also save as .js for local file access (CORS bypass)
    js_name = "news_data.js"
    js_content = f"window.NEWS_DATA = {json.dumps(combined_items, ensure_ascii=False, indent=2)};"
    with open(js_name, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"[OK] Wrote to {js_name} (for local browser access)")


if __name__ == "__main__":
    main()
