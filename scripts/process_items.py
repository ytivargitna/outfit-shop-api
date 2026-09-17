import os
import re
import json
import urllib.parse
import urllib.request
import ssl
import cairosvg
from concurrent.futures import ThreadPoolExecutor, as_completed

DEST_DIR = "/Users/Apple16/Desktop/SS_MIS/items"
os.makedirs(DEST_DIR, exist_ok=True)

# 1. Read the user input from transcript
log_path = "/Users/Apple16/.gemini/antigravity-ide/brain/b2ae896d-1d3a-4da4-9a4c-3d4b135d1332/.system_generated/logs/transcript_full.jsonl"
raw_items = []

with open(log_path, "r", encoding="utf-8") as f:
    for line in reversed(f.readlines()):
        data = json.loads(line)
        if data.get("type") == "USER_INPUT":
            content = data.get("content", "")
            if "if gif remove it" in content:
                # Extract all URLs and data URIs
                tokens = re.findall(r'(https?://[^\s<>"]+|data:image/[^\s<>"]+)', content)
                raw_items = tokens
                break

print(f"Extracted {len(raw_items)} raw items from user input.")

# Configure SSL context
ssl_context = ssl.create_default_context()
ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    'Sec-Fetch-Dest': 'image',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Site': 'cross-site',
    'Referer': 'https://us.louisvuitton.com/'
}

def clean_product_name(raw_name: str, ext: str = ".png") -> str:
    # Decode URL encoding
    name = urllib.parse.unquote(raw_name)
    
    # Strip existing extensions
    name = re.sub(r'\.(png|jpg|jpeg|svg|gif|webp)$', '', name, flags=re.IGNORECASE)
    
    # Remove brand names (louis-vuitton, louis vuitton, lv, etc.)
    name = re.sub(r'(?i)\blouis[-_ ]vuitton\b', '', name)
    name = re.sub(r'(?i)\blv\b', '', name)
    name = re.sub(r'(?i)\blvse\b', '', name)
    name = re.sub(r'(?i)\bMACC_BC_\b', '', name)
    name = re.sub(r'(?i)\bMEN_BC_\b', '', name)
    name = re.sub(r'(?i)\bM_BC_\b', '', name)
    name = re.sub(r'(?i)\bMKC-RTW-\b', '', name)
    
    # Replace multiple hyphens, underscores, dots with single space
    name = re.sub(r'[-_.]+', ' ', name)
    
    # Remove leading/trailing non-alphanumeric chars
    name = re.sub(r'^\s*[-_ ]+', '', name)
    name = re.sub(r'[-_ ]+\s*$', '', name)
    
    # Compress multiple spaces
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Title case words
    words = [w.capitalize() if not w.isupper() else w for w in name.split()]
    name = " ".join(words)
    
    if not name:
        name = "Product Item"
        
    return f"{name}{ext}"

# Group and Deduplicate items
# For web URLs, extract base image key and select highest resolution (wid)
unique_tasks = {}

for item in raw_items:
    # Rule 1: IF GIF -> REMOVE / SKIP
    if "data:image/gif" in item or ".gif" in item.lower():
        continue
        
    # Rule 2: IF SVG Data URI -> Convert to PNG
    if item.startswith("data:image/svg+xml"):
        # Extract SVG content
        svg_content = item.split(",", 1)[1]
        svg_xml = urllib.parse.unquote(svg_content)
        # Try to find a title or use SVG icon index
        title_match = re.search(r'<title>(.*?)</title>', svg_xml, re.IGNORECASE)
        title = title_match.group(1) if title_match else f"Icon {len(unique_tasks)+1}"
        cleaned_filename = clean_product_name(title, ext=".png")
        unique_tasks[f"svg_data_{len(unique_tasks)}"] = {
            "type": "svg_data",
            "data": svg_xml,
            "filename": cleaned_filename
        }
        continue

    # If it's a URL
    if item.startswith("http://") or item.startswith("https://"):
        parsed = urllib.parse.urlparse(item)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        
        # Check if SVG URL
        if path.lower().endswith(".svg"):
            base_name = os.path.basename(path)
            cleaned_filename = clean_product_name(base_name, ext=".png")
            unique_tasks[f"svg_url_{path}"] = {
                "type": "svg_url",
                "url": item,
                "filename": cleaned_filename
            }
            continue
            
        # Parse product image base path
        base_name = os.path.basename(path)
        if not base_name:
            continue
            
        # Determine resolution weight from wid / hei
        wid = int(query.get("wid", [1090])[0]) if "wid" in query else 1090
        
        # Base key for deduplication (same image file regardless of wid)
        base_key = path
        
        # File extension (prefer original or png)
        ext = os.path.splitext(path)[1]
        if not ext or ext.lower() in [".png", ".jpg", ".jpeg"]:
            ext = os.path.splitext(path)[1] or ".png"
            
        cleaned_filename = clean_product_name(base_name, ext=ext)
        
        if base_key not in unique_tasks or unique_tasks[base_key].get("wid", 0) < wid:
            unique_tasks[base_key] = {
                "type": "image_url",
                "url": item,
                "wid": wid,
                "filename": cleaned_filename,
                "base_name": base_name
            }

print(f"Total unique product items after deduplication & filtering: {len(unique_tasks)}")

# Handle filename collisions
final_filename_counts = {}
tasks_to_run = []

for key, task_info in unique_tasks.items():
    fn = task_info["filename"]
    base, ext = os.path.splitext(fn)
    if fn in final_filename_counts:
        final_filename_counts[fn] += 1
        new_fn = f"{base} {final_filename_counts[fn]}{ext}"
    else:
        final_filename_counts[fn] = 1
        new_fn = fn
    task_info["final_filename"] = new_fn
    tasks_to_run.append(task_info)

def process_single_task(task):
    target_path = os.path.join(DEST_DIR, task["final_filename"])
    
    if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
        return True, task["final_filename"], "Already exists"
        
    for attempt in range(4):
        try:
            if task["type"] == "svg_data":
                # Convert SVG string to PNG
                cairosvg.svg2png(bytestring=task["data"].encode('utf-8'), write_to=target_path)
                return True, task["final_filename"], "SVG Data converted to PNG"
                
            elif task["type"] == "svg_url":
                req = urllib.request.Request(task["url"], headers=HEADERS)
                with urllib.request.urlopen(req, context=ssl_context, timeout=20) as resp:
                    svg_data = resp.read()
                cairosvg.svg2png(bytestring=svg_data, write_to=target_path)
                return True, task["final_filename"], "SVG URL converted to PNG"
                
            elif task["type"] == "image_url":
                req = urllib.request.Request(task["url"], headers=HEADERS)
                with urllib.request.urlopen(req, context=ssl_context, timeout=20) as resp:
                    img_data = resp.read()
                with open(target_path, "wb") as f:
                    f.write(img_data)
                return True, task["final_filename"], f"Downloaded ({len(img_data)/1024:.1f} KB)"
                
        except Exception as e:
            if attempt == 3:
                return False, task["final_filename"], str(e)
            import time
            time.sleep(1)

success_count = 0
fail_count = 0

print("Starting concurrent download and conversion...")
with ThreadPoolExecutor(max_workers=16) as executor:
    futures = {executor.submit(process_single_task, task): task for task in tasks_to_run}
    for future in as_completed(futures):
        success, filename, msg = future.result()
        if success:
            success_count += 1
        else:
            fail_count += 1
            print(f"Failed: {filename} -> {msg}")

print(f"\nCompleted! Successfully processed {success_count} items. Failures: {fail_count}.")
print(f"All files saved into: {DEST_DIR}")
