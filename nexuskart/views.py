from django.shortcuts import render, redirect
from django.contrib import messages
from store.models import Product, ReviewRating

def landing(request):
    return render(request, 'landing.html')

def home(request):
    products = Product.objects.all().filter(is_available=True).order_by('created_date')
    reviews=None
    for product in products:
        reviews = ReviewRating.objects.filter(product_id=product.id, status=True)
    context = {
        'products': products,
        'reviews': reviews,
    }
    return render(request, 'home.html', context)

def csrf_failure(request, reason=""):
    messages.warning(request, "Your session expired because the page was open for too long. Please log in again to continue.")
    return redirect('login')

def pages_help(request):
    return render(request, 'pages/help.html')

def pages_shipping(request):
    return render(request, 'pages/shipping.html')

def pages_returns(request):
    return render(request, 'pages/returns.html')

def pages_privacy(request):
    return render(request, 'pages/privacy.html')

def pages_terms(request):
    return render(request, 'pages/terms.html')
