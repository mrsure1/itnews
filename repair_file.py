import sys

path = 'collect_news.py'
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# find where main ends
main_start = -1
for i, line in enumerate(lines):
    if 'def main():' in line:
        main_start = i
        # keep going to find the last valid if __name__
    if 'if __name__ == "__main__":' in line:
        # we want to stop after the next line '    main()'
        if i + 1 < len(lines) and 'main()' in lines[i+1]:
            last_valid_end = i + 2
            # but we need to be careful if there are multiples. 
            # Let's just find the FIRST one after main_start.

if main_start != -1:
    new_lines = lines[:main_start]
    # Re-append a clean main
    clean_main = [
        "def main():\n",
        "    json_name = \"news_data.json\"\n",
        "    existing_items = []\n",
        "    if os.path.exists(json_name):\n",
        "        try:\n",
        "            with open(json_name, \"r\", encoding=\"utf-8\") as f:\n",
        "                existing_items = json.load(f)\n",
        "        except Exception:\n",
        "            pass\n",
        "\n",
        "    now = datetime.now().isoformat()\n",
        "    print(\"--- Collecting News ---\")\n",
        "    \n",
        "    # 각 섹션별 데이터 수집\n",
        "    domestic_items = collect_domestic_news(now)\n",
        "    global_items = collect_global_news()\n",
        "    youtube_items = fetch_youtube_news()\n",
        "    \n",
        "    all_new_items = domestic_items + global_items + youtube_items\n",
        "    \n",
        "    seen_links = set()\n",
        "    combined_items = []\n",
        "    \n",
        "    # 1. 신규 아이템 추가 (중복 제거)\n",
        "    for item in all_new_items:\n",
        "        link = item.get(\"링크\") or item.get(\"link\")\n",
        "        if link and link not in seen_links:\n",
        "            seen_links.add(link)\n",
        "            combined_items.append(item)\n",
        "            \n",
        "    # 2. 기존 아이템 중 7일 이내 데이터 유지\n",
        "    seven_days_ago = datetime.now() - timedelta(days=7)\n",
        "    for item in existing_items:\n",
        "        link = item.get(\"링크\") or item.get(\"link\")\n",
        "        if link and link not in seen_links:\n",
        "            pub_date_str = item.get(\"수집일시\") or item.get(\"collected_at\", \"\")\n",
        "            try:\n",
        "                if \"T\" in pub_date_str:\n",
        "                    pub_date = datetime.fromisoformat(pub_date_str)\n",
        "                else:\n",
        "                    pub_date = datetime.strptime(pub_date_str, \"%Y-%m-%d %H:%M:%S\")\n",
        "                \n",
        "                if pub_date > seven_days_ago:\n",
        "                    seen_links.add(link)\n",
        "                    combined_items.append(item)\n",
        "            except Exception:\n",
        "                pass\n",
        "\n",
        "    # JSON 저장\n",
        "    with open(json_name, \"w\", encoding=\"utf-8\") as f:\n",
        "        json.dump(combined_items, f, ensure_ascii=False, indent=2)\n",
        "        \n",
        "    # JS 저장 (브라우저용)\n",
        "    js_content = f\"window.NEWS_DATA = {json.dumps(combined_items, ensure_ascii=False, indent=2)};\"\n",
        "    with open(\"news_data.js\", \"w\", encoding=\"utf-8\") as f:\n",
        "        f.write(js_content)\n",
        "        \n",
        "    print(f\"\\n[DONE] Total items: {len(combined_items)}\")\n",
        "\n",
        "if __name__ == \"__main__\":\n",
        "    main()\n"
    ]
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
        f.writelines(clean_main)
    print("Repair successful")
else:
    print("Could not find main start")
