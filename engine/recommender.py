def calculate_match_score(phone, user_prefs):
    """
    تحسب درجة التوافق بين هاتف واحد وتفضيلات المستخدم
    """
    score = 0.0
    reasons = []

    # -----------------
    # Price
    # -----------------
    if phone["price"] <= user_prefs["max_price"]:
        price_score = 1.0
        reasons.append("السعر ضمن ميزانيتك")
    else:
        price_score = user_prefs["max_price"] / phone["price"]
        reasons.append("السعر أعلى من الميزانية قليلًا")

    score += price_score * user_prefs["price_weight"]

    # -----------------
    # Camera
    # -----------------
    camera_score = phone.get("camera_score", 0)
    score += camera_score * user_prefs["camera_weight"]

    if camera_score >= 0.7:
        reasons.append("الكاميرا جيدة بالنسبة لتفضيلاتك")

    # -----------------
    # Battery
    # -----------------
    battery_score = phone.get("battery_score", 0)
    score += battery_score * user_prefs["battery_weight"]

    if battery_score >= 0.7:
        reasons.append("البطارية قوية وتناسب استخدامك")

    # -----------------
    # Performance
    # -----------------
    performance_score = phone.get("performance_score", 0)
    score += performance_score * user_prefs["performance_weight"]

    if performance_score >= 0.7:
        reasons.append("الأداء مناسب لتطبيقاتك اليومية")

    # -----------------
    # Screen
    # -----------------
    screen_score = phone.get("screen_score", 0)
    score += screen_score * user_prefs["screen_weight"]

    if screen_score >= 0.7:
        reasons.append("حجم وجودة الشاشة مريحان")

    return round(score, 3), reasons


def recommend_phones(phones, user_prefs, top_n=3):
    """
    ترتّب الهواتف وتعيد أفضل النتائج
    """
    results = []

    for phone in phones:
        score, reasons = calculate_match_score(phone, user_prefs)

        results.append({
            "name": phone["name"],
            "brand": phone["brand"],
            "price": phone["price"],
            "score": score,
            "reasons": reasons
        })

    # ترتيب تنازلي حسب درجة التوافق
    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:top_n]
