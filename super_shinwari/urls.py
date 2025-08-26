from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    # 🔧 Django Admin
    path('admin/', admin.site.urls),

    # 🔧 App Routes (core app)
    path('', include('core.urls')),

    # 🔐 Optional Auth Views (built-in login/logout if needed)
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]

# 📂 Media files served in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


