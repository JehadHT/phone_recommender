import csv
import os
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_service import PhoneChatService

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
    screen: Optional[float] = None

class ChatMessage(BaseModel):
    message: str

chat_service = PhoneChatService()


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
                "image_url": row.get("sketchfab_embed") or None,
                "screen": float(row["Screen size (inches)"]),
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
        # Price range (strict)
        if prefs.min_price is not None and phone["price"] < prefs.min_price:
            continue
        if prefs.max_price is not None and phone["price"] > prefs.max_price:
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

@app.post("/filter")
def recommend_by_specs(prefs: PhonePreferences):
    results = filter_phones(PHONES, prefs)
    return {
        "count": len(results),
        "results": results
    }


@app.post("/chat")
def chat_with_bot(data: ChatMessage):
    result = chat_service.chat(data.message)
    return {"reply": result.reply, "type": result.type}
