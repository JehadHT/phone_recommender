import csv
import os
import re
import requests
from typing import Optional, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Phone Recommender API",
    description="Advanced phone recommendation system with weighted scoring",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PhonePreferences(BaseModel):
    brand: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_battery: Optional[int] = None
    min_ram: Optional[int] = None
    min_camera_mp: Optional[int] = None

def load_phones_from_csv():
    csv_path = os.path.join("data", "phones.csv")
    phones = []

    with open(csv_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                camera_mp = int(float(row["Rear camera"]))
            except:
                camera_mp = 0

            phones.append({
                "name": row["Name"],
                "brand": row["Brand"],
                "price": float(row["Price"]),
                "battery": int(row["Battery capacity (mAh)"]),
                "ram": int(row["RAM (MB)"]),
                "camera_mp": camera_mp,
                "image_url": row.get("sketchfab_embed") or None
            })

    return phones

PHONES = load_phones_from_csv()

# ---------- قيم السوق القصوى ----------
MAX_PRICE = max(p["price"] for p in PHONES)
MAX_BATTERY = max(p["battery"] for p in PHONES)
MAX_RAM = max(p["ram"] for p in PHONES)
MAX_CAMERA = max(p["camera_mp"] for p in PHONES)

PRICE_RANGE = {
    "min": min(p["price"] for p in PHONES),
    "max": MAX_PRICE
}

def calculate_weights(prefs: PhonePreferences):
    weights = {}

    if prefs.max_price:
        weights["price"] = 1
    if prefs.min_battery:
        weights["battery"] = 1
    if prefs.min_ram:
        weights["ram"] = 1
    if prefs.min_camera_mp:
        weights["camera"] = 1
    if prefs.brand: 
        weights["brand"] = 1
 
    total = sum(weights.values()) or 1
    return {k: v / total for k, v in weights.items()}

def calculate_score(phone, prefs: PhonePreferences):
    weights = calculate_weights(prefs)
    score = 0
    reasons = []

    # ---------- السعر ----------
    if prefs.max_price:
        price_score = max(0, (prefs.max_price - phone["price"]) / prefs.max_price * 100)
        score += price_score * weights.get("price", 0)
        if phone["price"] <= prefs.max_price:
            reasons.append("Price within budget")

    # ---------- البطارية ----------
    battery_score = (phone["battery"] / MAX_BATTERY) * 100
    score += battery_score * weights.get("battery", 0)
    if prefs.min_battery and phone["battery"] >= prefs.min_battery:
        reasons.append("Strong battery")

    # ---------- RAM ----------
    ram_score = (phone["ram"] / MAX_RAM) * 100
    score += ram_score * weights.get("ram", 0)
    if prefs.min_ram and phone["ram"] >= prefs.min_ram:
        reasons.append("Good RAM capacity")

    # ---------- الكاميرا ----------
    camera_score = (phone["camera_mp"] / MAX_CAMERA) * 100
    score += camera_score * weights.get("camera", 0)
    if prefs.min_camera_mp and phone["camera_mp"] >= prefs.min_camera_mp:
        reasons.append("Camera meets requirements")

    # ---------- الماركة ----------
    if prefs.brand:
        brand_score = 100 if phone["brand"].lower() == prefs.brand.lower() else 0
        score += brand_score * weights.get("brand", 0)
        if brand_score:
            reasons.append(f"Preferred brand: {prefs.brand}")

    return round(score, 2), reasons

def filter_phones(phones, prefs: PhonePreferences):
    results = []

    for phone in phones:
        # فلترة ناعمة (استبعاد الحالات السيئة جدًا فقط)
        if prefs.max_price and phone["price"] > prefs.max_price * 1.3:
            continue
        if prefs.brand and phone["brand"].lower() != prefs.brand.lower():
            continue

        score, reasons = calculate_score(phone, prefs)

        phone_copy = phone.copy()
        phone_copy["match_percentage"] = score
        phone_copy["reasons"] = reasons

        results.append(phone_copy)

    results.sort(key=lambda x: x["match_percentage"], reverse=True)
    return results

@app.get("/")
def root():
    return {"message": "Phone Recommender API v2 is running 🚀"}
@app.get("/brands")
def get_brands():
    return sorted(set(p["brand"] for p in PHONES))
@app.get("/price-range")
def get_price_range():
    return PRICE_RANGE
@app.get("/stats")
def get_stats():
    return {
        "max_price": MAX_PRICE,
        "max_battery": MAX_BATTERY,
        "max_ram": MAX_RAM,
        "max_camera_mp": MAX_CAMERA
    }
@app.post("/filter")
def recommend_by_specs(prefs: PhonePreferences):
    results = filter_phones(PHONES, prefs)
    return {
        "count": len(results),
        "results": results
    }


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    """Lightweight chat endpoint: يحاول استخراج تفضيلات بسيطة من نص المستخدم ثم يعيد توصيات."""
    text = req.message or ""
    text_l = text.lower()

    prefs = PhonePreferences()

    # محاولة استخراج العلامة التجارية من الكلمات المعروفة
    brands = sorted(set(p["brand"] for p in PHONES), key=lambda x: -len(x))
    for b in brands:
        if b and b.lower() in text_l:
            prefs.brand = b
            break

    # أرقام في النص
    nums = re.findall(r"(\d+(?:\.\d+)?)", text_l)
    nums = [float(n) for n in nums]

    # قواعد بسيطة لاستخراج الحقول
    if "سعر" in text_l or "price" in text_l or "less" in text_l or "اقل" in text_l:
        if nums:
            prefs.max_price = nums[0]

    if "بطارية" in text_l or "battery" in text_l:
        # ابحث عن رقم بعد كلمة بطارية أو أول رقم
        if nums:
            prefs.min_battery = int(nums[0])

    if "رام" in text_l or "ram" in text_l:
        if nums:
            prefs.min_ram = int(nums[0])

    if "كاميرا" in text_l or "camera" in text_l:
        if nums:
            prefs.min_camera_mp = int(nums[0])

    # كخيار افتراضي إن لم نستخرج شيئًا
    results = filter_phones(PHONES, prefs)

    return {
        "message": "هذه بعض التوصيات بناءً على طلبك:",
        "recommendations": results[:8]
    }

