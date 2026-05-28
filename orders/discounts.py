from decimal import Decimal, ROUND_HALF_UP

from .models import Order


FIRST_ORDER_CODE = "FIRST40"
RETURNING_CODE = "RETURN10"
TAX_RATE = Decimal("0.02")

DISCOUNT_CODES = {
    FIRST_ORDER_CODE: {
        "percent": Decimal("40"),
        "label": "40% off your first order",
        "headline": "First order, 40% off",
        "body": "Use code FIRST40 at checkout and start your Nexuskart wardrobe for less.",
    },
    RETURNING_CODE: {
        "percent": Decimal("10"),
        "label": "10% off your next order",
        "headline": "Welcome back, take 10% off",
        "body": "Use code RETURN10 after your first purchase for a returning-member saving.",
    },
}


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def completed_order_count(user):
    if not getattr(user, "is_authenticated", False):
        return 0
    return Order.objects.filter(user=user, is_ordered=True).count()


def eligible_discount_code(user):
    if completed_order_count(user) > 0:
        return RETURNING_CODE
    return FIRST_ORDER_CODE


def promotion_offer(user):
    code = eligible_discount_code(user)
    offer = DISCOUNT_CODES[code].copy()
    offer["code"] = code
    return offer


def calculate_discount(user, subtotal, code):
    normalized_code = (code or "").strip().upper()
    subtotal = money(subtotal)
    eligible_code = eligible_discount_code(user)

    if not normalized_code:
        return {
            "code": "",
            "is_valid": False,
            "message": "",
            "percent": Decimal("0"),
            "discount_amount": Decimal("0.00"),
        }

    if normalized_code not in DISCOUNT_CODES:
        return {
            "code": normalized_code,
            "is_valid": False,
            "message": "This discount code does not exist.",
            "percent": Decimal("0"),
            "discount_amount": Decimal("0.00"),
        }

    if normalized_code != eligible_code:
        required_purchase_count = completed_order_count(user)
        if normalized_code == FIRST_ORDER_CODE and required_purchase_count > 0:
            message = "FIRST40 is only available before your first purchase."
        else:
            message = "RETURN10 unlocks after your first completed purchase."
        return {
            "code": normalized_code,
            "is_valid": False,
            "message": message,
            "percent": Decimal("0"),
            "discount_amount": Decimal("0.00"),
        }

    percent = DISCOUNT_CODES[normalized_code]["percent"]
    discount_amount = money(subtotal * percent / Decimal("100"))
    return {
        "code": normalized_code,
        "is_valid": True,
        "message": f"{DISCOUNT_CODES[normalized_code]['label']} applied.",
        "percent": percent,
        "discount_amount": discount_amount,
    }


def calculate_totals(user, subtotal, code=""):
    subtotal = money(subtotal)
    discount = calculate_discount(user, subtotal, code)
    discounted_subtotal = money(max(subtotal - discount["discount_amount"], Decimal("0.00")))
    tax = money(discounted_subtotal * TAX_RATE)
    grand_total = money(discounted_subtotal + tax)
    return {
        "total": subtotal,
        "discount": discount,
        "discount_code": discount["code"] if discount["is_valid"] else "",
        "discount_percent": discount["percent"] if discount["is_valid"] else Decimal("0"),
        "discount_amount": discount["discount_amount"],
        "discounted_subtotal": discounted_subtotal,
        "tax": tax,
        "grand_total": grand_total,
    }
