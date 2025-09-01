from decimal import Decimal
import stripe

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.db.models import Q, Sum, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import (
    Branch, Category, Product, Cart, CartItem,
    Order, OrderItem, Review, NewsletterSubscriber, Feedback,
    PointsTransaction
)
from .forms import (
    CategoryForm, ProductForm, OrderForm,
    ProductFilterForm, ReviewForm, ContactForm,
    NewsletterForm, OrderStatusForm, FeedbackForm, CustomUserCreationForm
)
from .loyalty import get_profile, apply_redemption, redeem_points, award_points_for_order

SESSION_BRANCH_KEY = "selected_branch_id"

# configure stripe api key from settings (ensure settings has STRIPE_SECRET_KEY)
stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", None)


# ---------------- Helpers ----------------
def _get_or_create_cart_for_user(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def _get_selected_branch(request):
    branch_id = request.session.get(SESSION_BRANCH_KEY)
    if branch_id:
        return Branch.objects.filter(id=branch_id).first()
    return None


# ---------------- Public Views ----------------
def home(request):
    selected_branch = _get_selected_branch(request)
    categories = Category.objects.all()
    category_products = {}
    for category in categories:
        qs = Product.objects.filter(category=category)
        if selected_branch:
            qs = qs.filter(Q(branch__isnull=True) | Q(branch=selected_branch))
        if qs.exists():
            category_products[category] = qs

    featured_products = Product.objects.filter(is_featured=True)
    if selected_branch:
        featured_products = featured_products.filter(Q(branch__isnull=True) | Q(branch=selected_branch))
    featured_products = featured_products[:8]

    available_branches = Branch.objects.all()

    return render(request, 'home.html', {
        'categories': categories,
        'category_products': category_products,
        'featured_products': featured_products,
        'selected_branch': selected_branch,
        'available_branches': available_branches,
    })


def full_menu(request):
    selected_branch = _get_selected_branch(request)
    categories = Category.objects.all()
    category_products = {}
    for category in categories:
        qs = Product.objects.filter(category=category)
        if selected_branch:
            qs = qs.filter(Q(branch__isnull=True) | Q(branch=selected_branch))
        if qs.exists():
            category_products[category] = qs
    return render(request, 'full_menu.html', {
        'category_products': category_products,
        'selected_branch': selected_branch
    })


def categories(request):
    return render(request, 'categories.html', {'categories': Category.objects.all()})


def products(request, category_id=None):
    """Products list with optional category filter and price filter."""
    selected_branch = _get_selected_branch(request)
    products_qs = Product.objects.all()

    category = None
    if category_id:
        category = get_object_or_404(Category, id=category_id)
        products_qs = products_qs.filter(category=category)

    if selected_branch:
        products_qs = products_qs.filter(Q(branch__isnull=True) | Q(branch=selected_branch))

    form = ProductFilterForm(request.GET or None)
    if form.is_valid():
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        if min_price is not None:
            products_qs = products_qs.filter(price__gte=min_price)
        if max_price is not None:
            products_qs = products_qs.filter(price__lte=max_price)

    categories_qs = Category.objects.all()

    return render(request, 'products.html', {
        'category': category,
        'products': products_qs,
        'filter_form': form,
        'categories': categories_qs,
        'selected_branch': selected_branch
    })


def search_products(request):
    query = request.GET.get('q', '').strip()
    products = Product.objects.filter(Q(name__icontains=query) | Q(description__icontains=query)) if query else Product.objects.none()
    return render(request, 'search_results.html', {'query': query, 'products': products})


def product_detail(request, product_id):
    """Single product detail with review form handling."""
    product = get_object_or_404(Product, id=product_id)
    reviews = Review.objects.filter(product=product).order_by('-created_at')
    related = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]

    form = ReviewForm(request.POST or None)
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.info(request, "Please login to submit a review.")
            return redirect('login')
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Review submitted.")
            return redirect('product_detail', product_id=product.id)
        else:
            messages.error(request, "There was a problem with your review submission.")

    return render(request, 'product_detail.html', {
        'product': product,
        'form': form,
        'reviews': reviews,
        'related': related
    })


# ---------------- Registration (single unified view) ----------------
def register(request):
    """
    Uses CustomUserCreationForm (which should handle Profile creation inside form.save()).
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # form.save() should create User and Profile if implemented there
            login(request, user)
            messages.success(request, "Account created and logged in.")
            return redirect('home')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})


# ---------------- Cart ----------------
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = _get_or_create_cart_for_user(request.user)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, defaults={'quantity': 1}
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, f"{product.name} added to cart.")
    return redirect('view_cart')


@login_required
def view_cart(request):
    cart = _get_or_create_cart_for_user(request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('product')
    total_price = Decimal('0.00')
    for item in cart_items:
        item_price = item.product.price or Decimal('0.00')
        item_total = item_price * item.quantity
        setattr(item, 'item_total', item_total)
        total_price += item_total
    return render(request, 'cart.html', {'cart_items': cart_items, 'total_price': total_price})


@login_required
@require_POST
def update_cart(request, item_id):
    cart = _get_or_create_cart_for_user(request.user)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    try:
        quantity = int(request.POST.get("quantity", 1))
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()
    except (ValueError, TypeError):
        messages.error(request, "Invalid quantity.")
    return redirect('view_cart')


@login_required
def remove_cart_item(request, item_id):
    cart = _get_or_create_cart_for_user(request.user)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('view_cart')


# ---------------- Checkout & Orders ----------------
@login_required
def checkout(request):
    cart = _get_or_create_cart_for_user(request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('product')
    if not cart_items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect('view_cart')

    form = OrderForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)
        order.user = request.user
        selected_branch = _get_selected_branch(request)
        if selected_branch:
            order.branch = selected_branch

        total_price = sum((item.product.price or Decimal('0.00')) * item.quantity for item in cart_items)
        order.total_price = total_price
        order.save()

        for item in cart_items:
            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity, price=item.product.price)
        cart_items.delete()

        # award loyalty points (safe call)
        try:
            award_points_for_order(request.user, order)
        except Exception:
            pass

        messages.success(request, "Order placed successfully.")
        return redirect("order_success")

    total = sum((item.product.price or Decimal('0.00')) * item.quantity for item in cart_items)
    return render(request, "checkout.html", {"cart_items": cart_items, "form": form, "total": total})


@login_required
def order_success(request):
    return render(request, "order_success.html")


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "order_detail.html", {"order": order})


@login_required
def track_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'track_order.html', {'order': order})


# ---------------- Admin Dashboard ----------------
@staff_member_required
def admin_dashboard(request):
    orders = Order.objects.all().order_by('-created_at')

    # Stats
    total_orders = orders.count()
    total_revenue = orders.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
    total_customers = User.objects.filter(is_superuser=False).count()

    # Chart data (status wise count)
    status_counts = orders.values('status').annotate(count=Count('status'))
    labels = [sc['status'] for sc in status_counts]
    data = [sc['count'] for sc in status_counts]

    return render(request, 'admin_dashboard.html', {
        'orders': orders,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_customers': total_customers,
        'labels': labels,
        'data': data
    })


@staff_member_required
def admin_orders(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'admin/manage_orders.html', {'orders': orders})


@staff_member_required
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    form = OrderStatusForm(request.POST or None, instance=order)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Order status updated.')
        return redirect('admin_orders')
    return render(request, 'admin/update_order_status.html', {'form': form, 'order': order})


# ---------------- Category / Product CRUD ----------------
@staff_member_required
def manage_categories(request):
    categories = Category.objects.all()
    return render(request, 'admin/manage_categories.html', {'categories': categories})


@staff_member_required
def add_category(request):
    form = CategoryForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Category added.")
        return redirect('manage_categories')
    return render(request, 'admin/add_category.html', {'form': form})


@staff_member_required
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, request.FILES or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Category updated.")
        return redirect('manage_categories')
    return render(request, 'admin/edit_category.html', {'form': form, 'category': category})


@staff_member_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    messages.success(request, "Category deleted.")
    return redirect('manage_categories')


@staff_member_required
def manage_products(request):
    products = Product.objects.all()
    return render(request, 'admin/manage_products.html', {'products': products})


@staff_member_required
def add_product(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Product added.")
        return redirect('manage_products')
    return render(request, 'admin/add_product.html', {'form': form})


@staff_member_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Product updated.")
        return redirect('manage_products')
    return render(request, 'admin/edit_product.html', {'form': form, 'product': product})


@staff_member_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, "Product deleted.")
    return redirect('manage_products')


# ---------------- Reviews ----------------
@login_required
@require_POST
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.product = product
        review.save()
        messages.success(request, "Review added.")
    else:
        messages.error(request, "Invalid review data.")
    return redirect('product_detail', product_id=product.id)


# ---------------- Contact ----------------
def contact(request):
    form = ContactForm(request.POST or None)
    success = False
    if request.method == 'POST' and form.is_valid():
        subject = form.cleaned_data['subject']
        message = (
            f"From: {form.cleaned_data['name']} <{form.cleaned_data['email']}>\n\n"
            f"{form.cleaned_data['message']}"
        )
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [settings.DEFAULT_FROM_EMAIL])
            success = True
            messages.success(request, 'Your message has been sent!')
        except Exception as e:
            messages.error(request, f"Error sending email: {e}")
    return render(request, 'contact.html', {'form': form, 'success': success})


# ---------------- Newsletter ----------------
def newsletter_signup(request):
    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            if not NewsletterSubscriber.objects.filter(email=email).exists():
                subscriber = form.save()
                try:
                    send_mail(
                        'Thank you for subscribing!',
                        'You have successfully subscribed to Super Shinwari Restaurant newsletter.',
                        settings.DEFAULT_FROM_EMAIL,
                        [subscriber.email],
                        fail_silently=False,
                    )
                    messages.success(request, 'Subscribed successfully! Please check your email.')
                except Exception:
                    messages.warning(request, 'Subscribed but email could not be sent.')
            else:
                messages.info(request, "You are already subscribed.")
        else:
            messages.error(request, "Invalid email.")
    return redirect(request.META.get('HTTP_REFERER', 'home'))


# ---------------- My account / Profile ----------------
@login_required
def my_account(request):
    return render(request, 'my_account.html', {
        'orders': Order.objects.filter(user=request.user).order_by('-created_at'),
        'reviews': Review.objects.filter(user=request.user).order_by('-created_at')
    })


@login_required
def profile(request):
    if request.method == 'POST':
        request.user.username = request.POST.get('username', request.user.username)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    return render(request, 'auth/profile.html')


# ---------------- Admin Login Redirect ----------------
class CustomAdminLoginView(LoginView):
    template_name = 'auth/admin_login.html'

    def get_success_url(self):
        return '/admin-dashboard/' if self.request.user.is_staff else '/'


# ---------------- Feedback ----------------
def feedback_view(request):
    form = FeedbackForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Thank you for your feedback!')
        return redirect('feedback')
    return render(request, 'feedback.html', {'form': form})


# ---------------- Branch selection ----------------
@require_POST
def select_branch(request):
    branch_id = request.POST.get('branch_id')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '/')
    if branch_id:
        try:
            branch = Branch.objects.get(pk=int(branch_id))
            request.session[SESSION_BRANCH_KEY] = branch.id
            messages.success(request, f"Branch selected: {branch.name}")
        except (Branch.DoesNotExist, ValueError):
            messages.error(request, "Selected branch not found.")
    else:
        messages.error(request, "No branch selected.")
    return redirect(next_url)


def select_branch_by_id(request, branch_id):
    branch = get_object_or_404(Branch, id=branch_id)
    request.session[SESSION_BRANCH_KEY] = branch.id
    messages.success(request, f"Branch selected: {branch.name}")
    return redirect(request.META.get('HTTP_REFERER', '/'))


def clear_branch(request):
    request.session.pop(SESSION_BRANCH_KEY, None)
    messages.success(request, "Branch selection cleared.")
    return redirect(request.META.get('HTTP_REFERER', '/'))


# ---------------- User Dashboard ----------------
@login_required
def user_dashboard(request):
    return render(request, 'user_dashboard.html')


# ---------------- Alternate Branch Setter ----------------
def set_branch(request, branch_id):
    """Alternate branch selector using the same SESSION_BRANCH_KEY."""
    request.session[SESSION_BRANCH_KEY] = branch_id
    messages.success(request, "Branch changed successfully.")
    return redirect('home')


# ---------------- Loyalty / Points (loyalty.py helpers used) ----------------
@login_required
def loyalty_dashboard(request):
    profile = get_profile(request.user)
    txns = PointsTransaction.objects.filter(user=request.user).order_by("-created_at")[:100]
    return render(request, "loyalty_dashboard.html", {
        "profile": profile,
        "transactions": txns
    })


@login_required
@require_POST
def apply_points(request):
    """
    Checkout page se POST: 'points' aur 'order_total' (Rs) bhejo.
    Hum session me 'loyalty_redeem' store kar denge.
    """
    try:
        points_requested = int(request.POST.get("points", 0))
        order_total = Decimal(request.POST.get("order_total", "0"))
    except Exception:
        messages.error(request, "Invalid points amount.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    points, discount = apply_redemption(request.user, points_requested, order_total)

    request.session["loyalty_redeem"] = {
        "points": points,
        "discount": str(discount),  # keep as str for JSON serializable
    }
    messages.success(request, f"Applied {points} points (discount Rs {discount}).")
    return redirect(request.META.get("HTTP_REFERER", "/"))


# ---------------- Stripe Checkout ----------------
@login_required
def create_checkout_session(request, order_id):
    """
    Create stripe checkout session for a given order.
    - ensures order exists and belongs to current user (or staff).
    - uses order.total_price if available, else tries order.total_amount.
    """
    order = get_object_or_404(Order, id=order_id)

    # authorize: user must own order or be staff
    if request.user != order.user and not request.user.is_staff:
        messages.error(request, "You are not authorized to pay for this order.")
        return redirect('my_orders')

    # determine order amount (Decimal)
    order_amount = getattr(order, "total_price", None) or getattr(order, "total_amount", None)
    if order_amount is None:
        messages.error(request, "Order has no amount set.")
        return redirect('order_detail', order_id=order.id)

    if not stripe.api_key:
        messages.error(request, "Payment gateway not configured. Contact admin.")
        return redirect('order_detail', order_id=order.id)

    try:
        # convert to integer cents/paisa (e.g., multiply by 100)
        unit_amount = int((Decimal(order_amount) * 100).quantize(Decimal('1.')))

        # choose currency from settings (default to PKR if not set) and ensure lowercase
        currency = getattr(settings, "PAYMENT_CURRENCY", "PKR").lower()

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'product_data': {
                        'name': f"Order #{order.id}",
                    },
                    'unit_amount': unit_amount,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri(f'/payment/success/?order={order.id}'),
            cancel_url=request.build_absolute_uri(f'/payment/cancel/?order={order.id}'),
        )
        return redirect(session.url, code=303)
    except stripe.error.StripeError as e:
        messages.error(request, f"Stripe error: {str(e)}")
        return redirect('order_detail', order_id=order.id)
    except Exception as e:
        messages.error(request, f"Payment initialization error: {e}")
        return redirect('order_detail', order_id=order.id)


def payment_success(request):
    return render(request, "payment_success.html")


def payment_cancel(request):
    return render(request, "payment_cancel.html")


from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

def register_user(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = UserCreationForm()
    return render(request, "auth/register.html", {"form": form})
