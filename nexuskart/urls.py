"""
URL configuration for nexuskart project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views
from django.conf.urls.static import static
from django.conf import settings
from accounts import views as accounts_views

urlpatterns = [
    path('admin-dashboard/', accounts_views.admin_dashboard, name='admin_dashboard_root'),
    path('admin/', include('admin_honeypot.urls', namespace='admin_honeypot')),
    path('securelogin/', admin.site.urls),
    path('', views.landing, name='landing'),
    path('shop/', views.home, name='home'),
    
    # Informative Pages
    path('help/', views.pages_help, name='help'),
    path('shipping/', views.pages_shipping, name='shipping'),
    path('returns/', views.pages_returns, name='returns'),
    path('privacy/', views.pages_privacy, name='privacy'),
    path('terms/', views.pages_terms, name='terms'),

    path('store/', include('store.urls')),
    path('cart/', include('carts.urls')),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),

    #ORDERS
    path('orders/', include('orders.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)