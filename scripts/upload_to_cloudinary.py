import os
import time
import hashlib
import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

CLOUD_NAME = 'od8t271n'
API_KEY = '292517627621863'
API_SECRET = 'CZhMlOoVVxAQBS_Vc_OrnPtqr4g'
ROOT_DIR = '/Users/Apple16/Desktop/product-items'
OUT_JSON = '/Users/Apple16/Desktop/backend/docs/catalog/cloudinary_live_urls.json'

def upload_single_image(img_path):
    rel_path = os.path.relpath(img_path, ROOT_DIR)
    folder_path = os.path.dirname(rel_path)
    filename = os.path.basename(img_path)
    public_id_base = os.path.splitext(filename)[0]

    timestamp = int(time.time())
    to_sign = f'folder={folder_path}&public_id={public_id_base}&timestamp={timestamp}{API_SECRET}'
    signature = hashlib.sha1(to_sign.encode('utf-8')).hexdigest()

    try:
        with open(img_path, 'rb') as fp:
            img_data = fp.read()
    except Exception as e:
        return {'status': 'error', 'file': rel_path, 'error': f'Read error: {e}'}

    boundary = f'----WebKitFormBoundary{hashlib.md5(filename.encode()).hexdigest()}'
    body = bytearray()

    def add_field(name, val):
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{val}\r\n'.encode('utf-8'))

    add_field('api_key', API_KEY)
    add_field('timestamp', str(timestamp))
    add_field('folder', folder_path)
    add_field('public_id', public_id_base)
    add_field('signature', signature)

    mime_type = 'image/png' if filename.lower().endswith('.png') else ('image/webp' if filename.lower().endswith('.webp') else 'image/jpeg')
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: {mime_type}\r\n\r\n'.encode('utf-8'))
    body.extend(img_data)
    body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

    req = urllib.request.Request(
        f'https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload',
        data=bytes(body),
        headers={
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'User-Agent': 'CloudinaryBulkUploader/2.0'
        }
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                resp = json.loads(res.read())
                return {
                    'status': 'success',
                    'file': rel_path,
                    'public_id': resp.get('public_id'),
                    'secure_url': resp.get('secure_url'),
                    'format': resp.get('format'),
                    'bytes': resp.get('bytes')
                }
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1 + attempt * 2)
            else:
                return {'status': 'error', 'file': rel_path, 'error': str(e)}

def main():
    print('Scanning all files in Desktop/product-items...')
    all_files = []
    for root, dirs, files in os.walk(ROOT_DIR):
        for f in files:
            if not f.startswith('.') and f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                all_files.append(os.path.join(root, f))

    total = len(all_files)
    print(f'Found {total} valid images to upload.')
    print('Starting multi-threaded upload (12 parallel threads)...')

    results = []
    completed = 0
    errors = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(upload_single_image, path): path for path in all_files}
        
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            completed += 1
            if res.get('status') == 'success':
                if completed % 50 == 0 or completed == total:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    print(f'Progress: {completed}/{total} ({completed/total*100:.1f}%) uploaded - {rate:.1f} img/sec')
            else:
                errors += 1
                print(f'Failed [{res.get("file")}]: {res.get("error")}')

    elapsed = time.time() - start_time
    print(f'\nFinished upload in {elapsed:.1f} seconds!')
    print(f' • Successfully uploaded: {completed - errors}')
    print(f' • Errors: {errors}')

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as fp:
        json.dump(results, fp, indent=2)

    print(f'Saved all live URLs to: {OUT_JSON}')

if __name__ == '__main__':
    main()
