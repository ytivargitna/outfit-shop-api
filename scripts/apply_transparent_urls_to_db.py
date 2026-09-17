import psycopg2
import re
import hashlib
import base64
import time

DB_HOST = 'ep-blue-mode-avbaa8zy-pooler.c-11.us-east-1.aws.neon.tech'
DB_PORT = 5432
DB_NAME = 'neondb'
DB_USER = 'neondb_owner'
DB_PASS = 'npg_SsC0GRvWm1Bz'

CLOUD_NAME = 'od8t271n'
API_SECRET = 'CZhMlOoVVxAQBS_Vc_OrnPtqr4g'

def sign_transparent(url):
    if not url or 'cloudinary.com' not in url:
        return url
    match = re.search(r'/image/upload/(?:s--[^/]+--/)?(?:e_[^/]+/)?(v[0-9]+/.+)$', url)
    if not match:
        return url
    path_part = match.group(1)
    trans = 'e_make_transparent'
    to_sign = f'{trans}/{path_part}{API_SECRET}'
    sig = base64.urlsafe_b64encode(hashlib.sha1(to_sign.encode('utf-8')).digest())[:8].decode('utf-8')
    return f'https://res.cloudinary.com/{CLOUD_NAME}/image/upload/s--{sig}--/{trans}/{path_part}'

def sql_escape(s):
    if s is None:
        return 'NULL'
    return "'" + str(s).replace("'", "''") + "'"

def batch_update_table(cur, table_name, id_col, rows, chunk_size=400):
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i+chunk_size]
        val_strs = [f"({row_id}, {sql_escape(new_url)})" for row_id, new_url in chunk]
        values_sql = ",".join(val_strs)
        sql = f"""
            UPDATE {table_name} AS t
            SET image_url = v.new_url, updated_at = NOW()
            FROM (VALUES {values_sql}) AS v({id_col}, new_url)
            WHERE t.{id_col} = v.{id_col};
        """
        cur.execute(sql)

def main():
    print('Connecting to Neon Database...', flush=True)
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        sslmode='require'
    )
    conn.autocommit = True
    cur = conn.cursor()

    # 1. Update Products
    print('1. Batch updating Products image_url...', flush=True)
    cur.execute('SELECT product_id, image_url FROM products WHERE image_url IS NOT NULL;')
    products = cur.fetchall()
    prod_updates = [(p_id, sign_transparent(orig_url)) for p_id, orig_url in products]
    batch_update_table(cur, 'products', 'product_id', prod_updates)
    print(f' • Updated {len(prod_updates)} products.', flush=True)

    # 2. Update Product Variants
    print('2. Batch updating Product Variants image_url...', flush=True)
    cur.execute('SELECT variant_id, image_url FROM product_variants WHERE image_url IS NOT NULL;')
    variants = cur.fetchall()
    var_updates = [(v_id, sign_transparent(orig_url)) for v_id, orig_url in variants]
    batch_update_table(cur, 'product_variants', 'variant_id', var_updates)
    print(f' • Updated {len(var_updates)} product variants.', flush=True)

    # 3. Update Product Images
    print('3. Batch updating Product Gallery Images image_url...', flush=True)
    cur.execute('SELECT image_id, image_url FROM product_images WHERE image_url IS NOT NULL;')
    images = cur.fetchall()
    img_updates = [(img_id, sign_transparent(orig_url)) for img_id, orig_url in images]
    batch_update_table(cur, 'product_images', 'image_id', img_updates)
    print(f' • Updated {len(img_updates)} gallery images.', flush=True)

    print('\nSUCCESS! All database image URLs are updated to transparent signed URLs.', flush=True)

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
