import aiohttp
import asyncio
import json
from pathlib import Path
from supabase import create_client, Client

SUPABASE_URL = "https://vgknohxqkkuxhtnqxzfb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZna25vaHhxa2t1eGh0bnF4emZiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzA2ODgxMSwiZXhwIjoyMDcyNjQ0ODExfQ.nVhvJtXR3_g611P0wkHwbHDeUyIWHjA5aiba9u5aQ9Q"

API_BASE_CONTENT = "https://api.oranosmarket.com/client/api/content/"
API_PRODUCTS = "https://api.oranosmarket.com/client/api/products"
API_TOKEN = "23ba0d3f9bdc1b755e775b2495a79df909cca80a77348d79"
HEADERS = {"api-token": API_TOKEN, "Accept": "application/json"}

CATEGORIES_TABLE = "categories"
SERVICES_TABLE = "services"

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

async def fetch_content(session, content_id):
    url = f"{API_BASE_CONTENT}{content_id}"
    try:
        async with session.get(url, headers=HEADERS, timeout=10) as resp:
            resp.raise_for_status()
            return await resp.json()
    except Exception as e:
        print(f"❌ Error fetching content {content_id}: {e}")
        return {}

async def fetch_products(session):
    try:
        async with session.get(API_PRODUCTS, headers=HEADERS, timeout=30) as resp:
            resp.raise_for_status()
            products = await resp.json()
            for p in products:
                p.pop("image_url", None)
                p.pop("category_img", None)
            return products
    except Exception as e:
        print(f"❌ Error fetching products: {e}")
        return []

async def build_category_tree(session, content_id=0):
    data = await fetch_content(session, content_id)
    categories = data.get("categories", [])
    tasks = [build_category_tree(session, cat["id"]) for cat in categories if cat["id"] != 14]
    subtrees = await asyncio.gather(*tasks, return_exceptions=True)
    tree = []
    for cat, sub in zip([c for c in categories if c["id"] != 14], subtrees):
        if isinstance(sub, Exception):
            sub = []
        tree.append({
            "id": cat.get("id"),
            "name": cat.get("name"),
            "subcategories": sub
        })
    return tree

def flatten_categories(categories, parent_id=None):
    flat = []
    for cat in categories:
        if cat["id"] == 14:
            continue
        flat.append({
            "id": cat["id"],
            "name": cat["name"],
            "parent_id": parent_id
        })
        if "subcategories" in cat:
            flat.extend(flatten_categories(cat["subcategories"], cat["id"]))
    return flat

def upsert_categories(supabase, categories):
    if not categories:
        print("⚠️ لا يوجد تصنيفات للإدخال.")
        return
    supabase.table(CATEGORIES_TABLE).upsert(categories, on_conflict="id").execute()
    print(f"✅ تم إدخال/تحديث {len(categories)} تصنيف دفعة واحدة")

def upsert_services(supabase, services):
    if not services:
        print("⚠️ لا يوجد خدمات للإدخال.")
        return
    supabase.table(SERVICES_TABLE).upsert(services, on_conflict="id").execute()
    print(f"✅ تم إدخال/تحديث {len(services)} خدمة دفعة واحدة")

def force_update_base_prices(supabase):
    res = supabase.table(SERVICES_TABLE).select("*").execute()
    services = res.data
    if not services:
        print("⚠️ لا توجد خدمات لتحديث base_price")
        return
    updated_services = []
    for s in services:
        category_id = s.get("category_id")
        if category_id == 14:
            continue
        price = float(s.get("price", 0))
        if price < 20:
            s["base_price"] = round(price * 1.20, 6)
        elif 20 <= price <= 40:
            s["base_price"] = round(price * 1.10, 6)
        else:
            s["base_price"] = round(price * 1.07, 6)
        updated_services.append(s)
    supabase.table(SERVICES_TABLE).upsert(updated_services, on_conflict="id").execute()
    print(f"✅ تم فرض تحديث base_price لـ {len(updated_services)} خدمة")

async def main():
    supabase = get_supabase_client()
    async with aiohttp.ClientSession() as session:
        print("⏳ جلب التصنيفات...")
        category_tree = await build_category_tree(session)
        c_json_path = Path("c.json")
        c_json_path.write_text(json.dumps(category_tree, ensure_ascii=False, indent=4), encoding="utf-8")
        print("⏳ جلب المنتجات...")
        products = await fetch_products(session)
        s_json_path = Path("s.json")
        s_json_path.write_text(json.dumps(products, ensure_ascii=False, indent=4), encoding="utf-8")
        print("✅ تم حفظ الملفات مؤقتاً")
    all_cats = flatten_categories(category_tree)
    upsert_categories(supabase, all_cats)
    payloads = []
    for item in products:
        category_id = item.get("parent_id")
        if category_id is None or category_id == 14:
            print(f"⚠️ الخدمة {item.get('name')} (id={item.get('id')}) مرتبطة بتصنيف محظور → تم تجاهلها")
            continue
        price = float(item.get("price", 0))
        if price < 20:
            base_price = round(price * 1.20, 6)
        elif 20 <= price <= 40:
            base_price = round(price * 1.10, 6)
        else:
            base_price = round(price * 1.07, 6)
        payload = {
            "id": item.get("id"),
            "name": item.get("name"),
            "price": price,
            "category_id": category_id,
            "params": item.get("params"),
            "available": item.get("available"),
            "qty_values": item.get("qty_values"),
            "product_type": item.get("product_type"),
            "base_price": base_price,
        }
        payload.pop("image_url", None)
        payload.pop("category_img", None)
        payloads.append(payload)
    upsert_services(supabase, payloads)
    force_update_base_prices(supabase)
    if c_json_path.exists():
        c_json_path.unlink()
    if s_json_path.exists():
        s_json_path.unlink()
    print("✅ تم حذف الملفات المؤقتة بعد إدخال البيانات")

if __name__ == "__main__":
    asyncio.run(main())
