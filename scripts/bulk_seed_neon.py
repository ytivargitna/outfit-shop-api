import os
import json
import psycopg2
import psycopg2.extras
import re
import random

DB_HOST = 'ep-blue-mode-avbaa8zy-pooler.c-11.us-east-1.aws.neon.tech'
DB_PORT = 5432
DB_NAME = 'neondb'
DB_USER = 'neondb_owner'
DB_PASS = 'npg_SsC0GRvWm1Bz'

URLS_JSON = '/Users/Apple16/Desktop/backend/docs/catalog/cloudinary_live_urls.json'
ROOT_DIR = '/Users/Apple16/Desktop/product-items'

BRAND_METADATA = {
    'Louis-Vuitton': {'name': 'Louis Vuitton', 'origin': 'France', 'desc': 'Iconic French luxury fashion house renowned for leather goods, haute couture, and trunk craftsmanship.', 'featured': True},
    'Stussy': {'name': 'Stussy', 'origin': 'United States', 'desc': 'Pioneering Californian streetwear brand fusing surf, skate, and hip-hop culture.', 'featured': True},
    'GitHub': {'name': 'GitHub', 'origin': 'United States', 'desc': 'Official developer merchandise, Invertocat apparel, and tech collectibles.', 'featured': True},
    'Lululemon': {'name': 'Lululemon', 'origin': 'Canada', 'desc': 'Premium technical athletic apparel for yoga, running, and training.', 'featured': True},
    'Palm-Angels': {'name': 'Palm Angels', 'origin': 'Italy', 'desc': 'Italian luxury streetwear label capturing the spirit of Los Angeles skate culture.', 'featured': True},
    'Pleasures': {'name': 'Pleasures', 'origin': 'United States', 'desc': 'Los Angeles streetwear brand rooted in punk, grunge, and 90s music subcultures.', 'featured': False},
    'Icecream': {'name': 'Icecream', 'origin': 'United States', 'desc': 'Playful streetwear and skate apparel by Pharrell Williams and NIGO.', 'featured': False},
    'Adidas': {'name': 'Adidas', 'origin': 'Germany', 'desc': 'Global sportswear giant blending athletic performance with streetwear style.', 'featured': True},
    'Google-Store': {'name': 'Google Store', 'origin': 'United States', 'desc': 'Official Google hardware, developer merchandise, and tech lifestyle apparel.', 'featured': True},
    'Maison-Margiela': {'name': 'Maison Margiela', 'origin': 'France', 'desc': 'Avant-garde Parisian fashion house celebrated for deconstructive luxury.', 'featured': True},
    'Godspeed': {'name': 'Godspeed', 'origin': 'United States', 'desc': 'Contemporary graphic streetwear and limited edition apparel.', 'featured': False},
    'Reese-Cooper': {'name': 'Reese Cooper', 'origin': 'United States', 'desc': 'American luxury heritage wear and utilitarian storytelling design.', 'featured': False},
    'Tesla': {'name': 'Tesla', 'origin': 'United States', 'desc': 'Official Tesla apparel, Cybercab merch, and minimalist tech lifestyle goods.', 'featured': True},
    'xAI-Grok': {'name': 'xAI Grok', 'origin': 'United States', 'desc': 'Official xAI & Grok apparel, trucker caps, thermal beanies, and drinkware.', 'featured': True},
    'Fear-of-God': {'name': 'Fear of God', 'origin': 'United States', 'desc': 'Jerry Lorenzo luxury streetwear and timeless Essentials collections.', 'featured': True},
    'Puma': {'name': 'Puma', 'origin': 'Germany', 'desc': 'Sportswear and football-inspired lifestyle collections.', 'featured': False},
    'Honour-The-Gift': {'name': 'Honour The Gift', 'origin': 'United States', 'desc': 'Russell Westbrook personal streetwear imprint celebrating inner-city resilience.', 'featured': False},
    'Market': {'name': 'Market', 'origin': 'United States', 'desc': 'Cult streetwear and graphic-forward lifestyle brand.', 'featured': False},
    'Nike': {'name': 'Nike', 'origin': 'United States', 'desc': 'World-renowned athletics and sneaker culture pioneer.', 'featured': True},
    'Kids-Worldwide': {'name': 'Kids Worldwide', 'origin': 'United States', 'desc': 'Youth and children fashion elevating community expression.', 'featured': False},
    'NBA': {'name': 'NBA', 'origin': 'United States', 'desc': 'Official National Basketball Association lifestyle and fan apparel.', 'featured': False},
    'Born-x-Raised': {'name': 'Born x Raised', 'origin': 'United States', 'desc': 'Venice Beach streetwear brand honoring authentic Los Angeles culture.', 'featured': False},
    'Jordan': {'name': 'Jordan', 'origin': 'United States', 'desc': 'Legendary basketball footwear and athletic heritage brand.', 'featured': True},
    'The-Boring-Company': {'name': 'The Boring Company', 'origin': 'United States', 'desc': 'Official industrial tech apparel, Cutterhead hats, and tunnel gear.', 'featured': False},
}

CATEGORIES = [
    ('T-Shirts & Tops', 'T-Shirts-and-Tops', 'APPAREL', 'Graphic tees, polos, jerseys, long sleeves, and shirts'),
    ('Hoodies & Sweatshirts', 'Hoodies-and-Sweatshirts', 'APPAREL', 'Pullover hoodies, crewnecks, sweaters, and fleece'),
    ('Jackets & Outerwear', 'Jackets-and-Outerwear', 'APPAREL', 'Track jackets, coats, windbreakers, and bombers'),
    ('Pants & Shorts', 'Pants-and-Shorts', 'APPAREL', 'Denim jeans, sweatpants, track pants, trousers, and shorts'),
    ('Footwear & Sneakers', 'Footwear-and-Sneakers', 'FOOTWEAR', 'Luxury sneakers, runners, slides, and footwear'),
    ('Hats & Headwear', 'Hats-and-Headwear', 'ACCESSORIES', 'Caps, trucker hats, 5-panel hats, beanies, and headwear'),
    ('Bags & Luggage', 'Bags-and-Luggage', 'ACCESSORIES', 'Totes, backpacks, crossbody bags, handbags, and travel luggage'),
    ('Drinkware & Bottles', 'Drinkware-and-Bottles', 'LIFESTYLE', 'Camp mugs, travel tumblers, bottles, and drinkware'),
    ('Stickers & Decals', 'Stickers-and-Decals', 'LIFESTYLE', 'Sticker packs, vinyl decals, and collectible pins'),
    ('Accessories & Lifestyle', 'Accessories-and-Lifestyle', 'LIFESTYLE', 'Keychains, plushes, desk mats, lifestyle goods, and collectibles'),
    ("Men's Activewear", 'Mens-Activewear', 'APPAREL', 'Technical performance activewear, training shorts, and tops for men'),
    ("Women's Activewear", 'Womens-Activewear', 'APPAREL', 'Yoga tights, leggings, athletic tops, and activewear for women'),
    ('Ready-to-Wear & Luxury Goods', 'Ready-to-Wear-and-Luxury-Goods', 'LUXURY', 'High fashion runway apparel and bespoke luxury goods'),
    ('Streetwear & Graphic Tops', 'Streetwear-and-Graphic-Tops', 'APPAREL', 'Classic streetwear silhouettes and graphic lookbooks'),
    ('Apparel & Merchandise', 'Apparel-and-Merchandise', 'APPAREL', 'Official branded merchandise and tech lifestyle apparel'),
]

def main():
    print('Connecting to Neon PostgreSQL Database...')
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

    print('1. Resetting all catalog tables...')
    cur.execute('''
        TRUNCATE TABLE 
            product_images,
            product_variants,
            products,
            categories,
            brands,
            clothing_sizes,
            colors
        RESTART IDENTITY CASCADE;
    ''')

    print('2. Seeding Clothing Sizes & Colors...')
    sizes = [
        ('Extra Small (XS)', 'Chest 34 inch'),
        ('Small (S)', 'Chest 36 inch'),
        ('Medium (M)', 'Chest 38 inch'),
        ('Large (L)', 'Chest 40 inch'),
        ('Extra Large (XL)', 'Chest 42 inch'),
        ('Double Extra Large (XXL)', 'Chest 44 inch'),
        ('One Size (OS)', 'Universal / Free Size')
    ]
    for s_name, desc in sizes:
        cur.execute('INSERT INTO clothing_sizes (size_name, description, created_at, updated_at) VALUES (%s, %s, NOW(), NOW());', (s_name, desc))

    cur.execute('SELECT size_name, size_id FROM clothing_sizes;')
    size_map = dict(cur.fetchall())

    colors = [
        ('Classic Black', '#000000'),
        ('Pure White', '#FFFFFF'),
        ('Navy Blue', '#000080'),
        ('Charcoal Gray', '#4A4A4A'),
        ('Vintage Green', '#2E8B57'),
        ('Crimson Red', '#DC143C'),
        ('Sand / Beige', '#F5F5DC')
    ]
    for c_name, hex_code in colors:
        cur.execute('INSERT INTO colors (color_name, description, created_at, updated_at) VALUES (%s, %s, NOW(), NOW());', (c_name, hex_code))

    cur.execute("SELECT color_id FROM colors WHERE color_name = 'Classic Black';")
    color_black_id = cur.fetchone()[0]

    print('3. Seeding 24 Brands...')
    brand_map = {}
    for folder_slug, meta in BRAND_METADATA.items():
        cur.execute('''
            INSERT INTO brands (brand_name, slug, country_of_origin, description, is_featured, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING brand_id;
        ''', (meta['name'], folder_slug.lower(), meta['origin'], meta['desc'], meta['featured']))
        b_id = cur.fetchone()[0]
        brand_map[folder_slug] = (b_id, meta['name'])

    print('4. Seeding 15 Categories...')
    cat_map = {}
    for c_name, c_slug, dept, desc in CATEGORIES:
        cur.execute('''
            INSERT INTO categories (category_name, slug, department_type, description, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            RETURNING category_id;
        ''', (c_name, c_slug.lower(), dept, desc))
        c_id = cur.fetchone()[0]
        cat_map[c_slug] = c_id
        cat_map[c_name] = c_id

    default_cat_id = cat_map.get('Apparel-and-Merchandise', 1)

    print('5. Loading Cloudinary Live URL map...')
    with open(URLS_JSON, 'r', encoding='utf-8') as fp:
        urls_data = json.load(fp)

    cloudinary_url_map = {}
    for item in urls_data:
        f = item.get('file')
        if f:
            cloudinary_url_map[f] = item.get('secure_url')

    print(f'Loaded {len(cloudinary_url_map)} Cloudinary CDN URLs.')

    print('6. Grouping and Preparing Products from Desktop/product-items...')
    products_to_insert = []
    products_metadata = []

    for brand_folder, (brand_id, brand_name) in brand_map.items():
        b_path = os.path.join(ROOT_DIR, brand_folder)
        if not os.path.isdir(b_path):
            continue

        for cat_folder in os.listdir(b_path):
            c_path = os.path.join(b_path, cat_folder)
            if not os.path.isdir(c_path) or cat_folder.startswith('.'):
                continue

            cat_id = cat_map.get(cat_folder, default_cat_id)
            img_files = sorted([f for f in os.listdir(c_path) if not f.startswith('.') and f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])

            product_groups = {}
            for img_f in img_files:
                name_no_ext = os.path.splitext(img_f)[0]
                base_title = re.sub(r'_[0-9]+$', '', name_no_ext).strip()
                # Format human readable title
                title_words = base_title.replace('-', ' ').replace('_', ' ')
                clean_title = ' '.join(word.capitalize() for word in title_words.split())

                if clean_title not in product_groups:
                    product_groups[clean_title] = []
                
                rel_f_path = f'{brand_folder}/{cat_folder}/{img_f}'
                product_groups[clean_title].append(rel_f_path)

            for prod_title, rel_files in product_groups.items():
                primary_rel_file = rel_files[0]
                primary_url = cloudinary_url_map.get(primary_rel_file, f'https://res.cloudinary.com/od8t271n/image/upload/{primary_rel_file}')

                base_price = (
                    random.randint(450, 1850) if brand_name in ['Louis Vuitton', 'Maison Margiela'] else
                    random.randint(180, 480) if brand_name in ['Palm Angels', 'Fear of God', 'Reese Cooper'] else
                    random.randint(65, 160) if brand_name in ['Lululemon', 'Stussy', 'Pleasures', 'Icecream', 'Godspeed', 'Born x Raised', 'Honour The Gift'] else
                    random.randint(35, 120) if brand_name in ['Tesla', 'xAI Grok', 'The Boring Company'] else
                    random.randint(25, 75) if brand_name in ['GitHub', 'Google Store'] else
                    random.randint(40, 120)
                )

                gender = 'WOMEN' if 'women' in cat_folder.lower() else ('MEN' if 'men' in cat_folder.lower() else 'UNISEX')
                is_featured = BRAND_METADATA.get(brand_folder, {}).get('featured', False)
                badge = 'FEATURED' if is_featured else None

                products_to_insert.append((
                    cat_id,
                    brand_id,
                    'PHYSICAL_APPAREL',
                    prod_title,
                    brand_name,
                    gender,
                    '100% Premium Cotton / Technical Blend',
                    'Annual Collection 2026',
                    f'Official {brand_name} {prod_title} crafted with authentic materials.',
                    primary_url,
                    badge,
                    'ACTIVE'
                ))

                products_metadata.append({
                    'title': prod_title,
                    'brand_slug': brand_folder,
                    'cat_folder': cat_folder,
                    'base_price': base_price,
                    'rel_files': rel_files,
                    'primary_url': primary_url
                })

    print(f'7. Bulk inserting {len(products_to_insert)} products in chunks...')
    inserted_product_ids = []

    insert_prod_sql = '''
        INSERT INTO products (category_id, brand_id, product_type, product_name, brand, gender, material_fabric, season_collection, description, image_url, featured_badge, status, created_at, updated_at)
        VALUES %s
        RETURNING product_id;
    '''

    for i in range(0, len(products_to_insert), 200):
        chunk = products_to_insert[i:i+200]
        res = psycopg2.extras.execute_values(
            cur,
            '''
            INSERT INTO products (category_id, brand_id, product_type, product_name, brand, gender, material_fabric, season_collection, description, image_url, featured_badge, status, created_at, updated_at)
            VALUES %s
            RETURNING product_id
            ''',
            chunk,
            template='(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())',
            fetch=True
        )
        inserted_product_ids.extend([row[0] for row in res])

    print(f'Successfully inserted {len(inserted_product_ids)} products!')

    print('8. Generating Variants and Image records...')
    variants_to_insert = []
    images_to_insert = []

    for idx, p_id in enumerate(inserted_product_ids):
        meta = products_metadata[idx]
        b_slug = meta['brand_slug']
        cat_f = meta['cat_folder']
        base_p = meta['base_price']
        cost_p = round(base_p * 0.45, 2)
        whole_p = round(base_p * 0.80, 2)

        is_one_size = cat_f in ['Hats-and-Headwear', 'Drinkware-and-Bottles', 'Stickers-and-Decals', 'Bags-and-Luggage', 'Accessories-and-Lifestyle']
        size_list = [('One Size (OS)', 'OS')] if is_one_size else [('Small (S)', 'SM'), ('Medium (M)', 'MD'), ('Large (L)', 'LG'), ('Extra Large (XL)', 'XL')]

        for s_name, s_code in size_list:
            s_id = size_map.get(s_name, 1)
            sku = f"{b_slug[:3].upper()}-{p_id}-{s_code}"
            barcode = f"885{str(p_id).zfill(6)}{str(s_id).zfill(3)}"
            qty = random.randint(25, 80)

            variants_to_insert.append((
                p_id,
                s_id,
                color_black_id,
                sku,
                barcode,
                cost_p,
                base_p,
                whole_p,
                qty,
                10,
                meta['primary_url']
            ))

        for f_idx, rel_path in enumerate(meta['rel_files']):
            img_cdn_url = cloudinary_url_map.get(rel_path, f'https://res.cloudinary.com/od8t271n/image/upload/{rel_path}')
            is_primary = (f_idx == 0)
            sort_order = f_idx + 1
            alt = f"{meta['title']} angle {sort_order}"

            images_to_insert.append((
                p_id,
                img_cdn_url,
                is_primary,
                sort_order,
                alt
            ))

    print(f'9. Bulk inserting {len(variants_to_insert)} product variants...')
    for i in range(0, len(variants_to_insert), 300):
        chunk = variants_to_insert[i:i+300]
        psycopg2.extras.execute_values(
            cur,
            '''
            INSERT INTO product_variants (product_id, size_id, color_id, sku, barcode, cost_price, sale_price, wholesale_price, quantity, reorder_level, image_url, created_at, updated_at)
            VALUES %s
            ''',
            chunk,
            template='(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())'
        )

    print(f'10. Bulk inserting {len(images_to_insert)} product gallery images...')
    for i in range(0, len(images_to_insert), 300):
        chunk = images_to_insert[i:i+300]
        psycopg2.extras.execute_values(
            cur,
            '''
            INSERT INTO product_images (product_id, image_url, is_primary, sort_order, alt_text, created_at, updated_at)
            VALUES %s
            ''',
            chunk,
            template='(%s, %s, %s, %s, %s, NOW(), NOW())'
        )

    print('\n========================================================')
    print('DATABASE SEEDING COMPLETE WITH 100% RELATIONAL INTEGRITY!')
    print('========================================================')
    print(f' • Total Brands: {len(brand_map)}')
    print(f' • Total Categories: {len(CATEGORIES)}')
    print(f' • Total Clothing Sizes: {len(size_map)}')
    print(f' • Total Colors: {len(colors)}')
    print(f' • Total Products: {len(inserted_product_ids)}')
    print(f' • Total Product Variants: {len(variants_to_insert)}')
    print(f' • Total Product Images: {len(images_to_insert)}')

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
