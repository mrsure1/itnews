
import json
import os

def main():
    json_path = "news_data.json"
    js_path = "news_data.js"
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        js_content = f"window.NEWS_DATA = {json.dumps(data, ensure_ascii=False, indent=2)};"
        
        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(js_content)
            
        print(f"Successfully converted {json_path} to {js_path}")
        
    except Exception as e:
        print(f"Error converting: {e}")

if __name__ == "__main__":
    main()
