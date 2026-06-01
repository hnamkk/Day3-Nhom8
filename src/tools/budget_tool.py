def calculate_budget(
    hotel_cost: int,
    days: int,
    flight_cost: int,
    food_daily: int,
    total_budget: int = 0,
) -> str:
    """Tính toán và kiểm tra tổng ngân sách chuyến đi.

    Args:
        hotel_cost:    Chi phí khách sạn mỗi đêm (VND).
        days:          Số ngày của chuyến đi.
        flight_cost:   Tổng chi phí vé máy bay khứ hồi (VND).
        food_daily:    Chi phí ăn uống / di chuyển mỗi ngày (VND).
        total_budget:  Tổng ngân sách người dùng có (VND).
                       Nếu = 0 thì chỉ tính tổng, không so sánh.

    Returns:
        Chuỗi văn bản phân tích ngân sách chi tiết.
    """
    if days <= 0:
        return "Số ngày chuyến đi phải lớn hơn 0."
    if hotel_cost < 0 or flight_cost < 0 or food_daily < 0:
        return "Các chi phí không được âm."

    # --- Detailed cost breakdown ---
    total_hotel = hotel_cost * days
    total_food = food_daily * days
    # Add a 10 % buffer for miscellaneous expenses (shopping, entry fees, etc.)
    misc = int((total_hotel + total_food + flight_cost) * 0.10)
    grand_total = total_hotel + total_food + flight_cost + misc

    lines = [
        "💰 PHÂN TÍCH NGÂN SÁCH CHUYẾN ĐI",
        "=" * 40,
        f"📅 Số ngày          : {days} ngày",
        f"🏨 Chi phí khách sạn: {hotel_cost:>12,} VND/đêm × {days} ngày = {total_hotel:,} VND",
        f"✈️  Vé máy bay (khứ hồi): {flight_cost:>8,} VND",
        f"🍜 Ăn uống & di chuyển: {food_daily:>8,} VND/ngày × {days} ngày = {total_food:,} VND",
        f"🛍️  Chi phí phát sinh (10%): {misc:,} VND",
        "-" * 40,
        f"💵 TỔNG CHI PHÍ DỰ KIẾN: {grand_total:,} VND",
    ]

    if total_budget > 0:
        lines.append("-" * 40)
        remaining = total_budget - grand_total
        if remaining >= 0:
            pct_used = (grand_total / total_budget) * 100
            lines.append(f"✅ Ngân sách của bạn  : {total_budget:,} VND")
            lines.append(
                f"✅ Còn dư             : {remaining:,} VND "
                f"(đã dùng {pct_used:.1f}%)"
            )
            if remaining >= 500_000:
                lines.append(
                    "💡 Gợi ý: Bạn có thể nâng cấp khách sạn hoặc thêm 1 tour trải nghiệm!"
                )
        else:
            over = abs(remaining)
            pct_over = (over / total_budget) * 100
            lines.append(f"❌ Ngân sách của bạn  : {total_budget:,} VND")
            lines.append(
                f"❌ Vượt ngân sách     : {over:,} VND ({pct_over:.1f}% vượt mức)"
            )
            lines.append("💡 Gợi ý để cắt giảm chi phí:")
            if hotel_cost > 500_000:
                lines.append(
                    f"   • Chọn khách sạn rẻ hơn (tiết kiệm ~{hotel_cost * days // 2:,} VND)"
                )
            if food_daily > 300_000:
                lines.append(
                    f"   • Ăn uống tiết kiệm hơn (~200,000 VND/ngày, tiết kiệm "
                    f"{(food_daily - 200_000) * days:,} VND)"
                )
            lines.append("   • Tìm vé máy bay sớm để được giá tốt hơn.")

    # Per-person cost hint (assuming 1 person; user can scale)
    lines.append("=" * 40)
    lines.append(
        f"📊 Chi phí trung bình mỗi ngày: {grand_total // days:,} VND/ngày"
    )

    return "\n".join(lines)
