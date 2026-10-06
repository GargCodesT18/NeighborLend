from app.constants import CATEGORY_DAILY_RATE

def suggest_price_per_day(category: str, years_owned: float, price_bought: float) -> dict:
    # Simple depreciation logic
    depreciation_rate = 0.10  # 10% per year
    current_value = price_bought * ((1 - depreciation_rate) ** years_owned)
    current_value = max(current_value, price_bought * 0.1)  # Minimum 10% of original price

    daily_rate = CATEGORY_DAILY_RATE.get(category, CATEGORY_DAILY_RATE["Other"])
    suggested_price = current_value * daily_rate

    return {
        "suggested_price_per_day": round(suggested_price, 2),
        "current_value_estimate": round(current_value, 2),
        "daily_rate_used": daily_rate,
        "explanation": f"Estimated current value: ₹{round(current_value, 2)} based on {years_owned} years of ownership. Daily rate applied: {daily_rate * 100}% of current value."
    }
