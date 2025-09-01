from django import forms
from .models import (
    Branch, Category, Product, Order, Review,
    ContactMessage, NewsletterSubscriber, Feedback, Profile  # Profile add karna hoga
)
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

# ============================
#       Branch Form
# ============================
class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['name', 'address', 'city', 'phone', 'is_main']


# ============================
#       Category Form
# ============================
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'image']


# ============================
#       Product Form
# ============================
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'branch', 'name', 'description', 'price', 'image', 'available']


# ============================
#        Order Form
# ============================
class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['full_name', 'phone', 'address']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# ============================
#     Product Filter Form
# ============================
class ProductFilterForm(forms.Form):
    min_price = forms.DecimalField(
        required=False,
        label='Min Price',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    max_price = forms.DecimalField(
        required=False,
        label='Max Price',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )


# ============================
#        Review Form
# ============================
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, i) for i in range(1, 6)], attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# ============================
#       Contact Form
# ============================
class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }


# ============================
#     Newsletter Form
# ============================
class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}),
        }


# ============================
#    Order Status Form (Admin)
# ============================
class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'})
        }


# ============================
#       Feedback Form
# ============================
class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['name', 'email', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }


# ============================
#   Custom User Creation Form
# ============================
class CustomUserCreationForm(UserCreationForm):
    phone = forms.CharField(max_length=15, required=True)
    address = forms.CharField(widget=forms.Textarea, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'phone', 'address']

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Profile model me extra data save karna
            Profile.objects.create(
                user=user,
                phone=self.cleaned_data['phone'],
                address=self.cleaned_data['address']
            )
        return user
