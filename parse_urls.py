import json
import re

log_path = "/Users/Apple16/.gemini/antigravity-ide/brain/b2ae896d-1d3a-4da4-9a4c-3d4b135d1332/.system_generated/logs/transcript_full.jsonl"
urls = []
with open(log_path, "r") as f:
    lines = f.readlines()
    for line in reversed(lines):
        data = json.loads(line)
        if data.get("type") == "USER_INPUT":
            content = data.get("content", "")
            if "if gif remove it" in content:
                urls = re.findall(r'(https?://\S+)', content)
                break

print(f"Found {len(urls)} URLs")
with open("extracted_urls.txt", "w") as f:
    for url in urls:
        f.write(url + "\n")
