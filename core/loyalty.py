# core/loyalty.py
from decimal import Decimal, ROUND_DOWN
from django.conf import settings
from .models import UserProfile, PointsTransaction

def get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile

def calc_points_earned(total_amount: Decimal) -> int:
    if total_amount is None:
        return 0
    pts = (total_amount * settings.LOYALTY_EARN_RATE).to_integral_value(rounding=ROUND_DOWN)
    return int(pts)

def max_redeemable_points(user, order_total: Decimal) -> int:
    profile = get_profile(user)
    # Rs value per point
    max_by_total = int(order_total / settings.LOYALTY_POINT_VALUE)
    return max(0, min(profile.points_balance, max_by_total))

def apply_redemption(user, requested_points: int, order_total: Decimal):
    """Clamp request to allowed range; return (points_to_use, discount_amount)."""
    requested_points = max(0, int(requested_points or 0))
    points = min(requested_points, max_redeemable_points(user, order_total))
    discount = settings.LOYALTY_POINT_VALUE * Decimal(points)
    return points, discount

def award_points_for_order(user, order_total: Decimal, order_id: str = "") -> int:
    """Give points after successful order. Returns points earned."""
    pts = calc_points_earned(order_total)
    if pts <= 0:
        return 0
    profile = get_profile(user)
    profile.points_balance += pts
    profile.save(update_fields=["points_balance"])
    PointsTransaction.objects.create(
        user=user, kind=PointsTransaction.EARN, points=pts,
        amount=order_total or Decimal("0"), order_id=str(order_id), note="Order reward"
    )
    return pts

def redeem_points(user, points_to_use: int, order_total: Decimal, order_id: str = "") -> Decimal:
    """Deduct points and create transaction. Returns discount Rs."""
    points, discount = apply_redemption(user, points_to_use, order_total)
    if points <= 0:
        return Decimal("0")
    profile = get_profile(user)
    profile.points_balance -= points
    profile.save(update_fields=["points_balance"])
    PointsTransaction.objects.create(
        user=user, kind=PointsTransaction.REDEEM, points=points,
        amount=discount, order_id=str(order_id), note="Redeemed on order"
    )
    return discount
