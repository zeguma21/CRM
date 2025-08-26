# core/context_processors.py
from django.db.models import Sum
from .models import Branch, Cart, CartItem

# ---------------------------
# Branch Context
# ---------------------------
def branch_context(request):
    """
    Adds available branches and selected branch (from session) to templates.
    """
    branches = Branch.objects.all()
    selected_branch = None
    selected_id = request.session.get('selected_branch')

    if selected_id:
        try:
            selected_branch = Branch.objects.get(id=selected_id)
        except Branch.DoesNotExist:
            selected_branch = None

    return {
        'available_branches': branches,
        'selected_branch': selected_branch
    }


# ---------------------------
# Cart Item Count (for navbar badge)
# ---------------------------
def cart_item_count(request):
    """
    Returns total quantity in the authenticated user's cart (sum of CartItem.quantity).
    """
    total = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            total = CartItem.objects.filter(cart=cart).aggregate(total=Sum('quantity'))['total'] or 0

    return {'cart_item_count': total}


# ---------------------------
# Cart + Branch + Loyalty Context (Main)
# ---------------------------
def cart_and_branch_context(request):
    """
    Provides cart items, cart total, active branch, and loyalty balance.
    """
    cart_items = []
    cart_total = 0
    active_branch = None
    loyalty_balance = 0

    # ✅ User ka cart fetch
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_items = cart.cart_items.select_related('product')
            cart_total = sum(item.product.price * item.quantity for item in cart_items)

        # ✅ Active Branch
        active_branch = Branch.objects.filter(is_main=True).first()
        if not active_branch:
            active_branch = Branch.objects.first()

        # ✅ Loyalty Balance
        try:
            from .loyalty import get_profile
            loyalty_balance = get_profile(request.user).points_balance
        except Exception:
            loyalty_balance = 0

    else:
        # Guest user
        active_branch = Branch.objects.filter(is_main=True).first() or Branch.objects.first()
        loyalty_balance = 0

    return {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'active_branch': active_branch,
        'loyalty_balance': loyalty_balance,
    }
