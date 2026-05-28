from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, ReviewRating, ProductGallery, WishlistItem
from category.models import Category
from carts.views import _cart_id
from carts.models import CartItem
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q

from carts.views import _cart_id
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from .forms import ReviewForm
from django.contrib import messages
from orders.models import OrderProduct
# Create your views here.
def store(request, category_slug=None):
    categories = None
    products = Product.objects.all().filter(is_available=True).order_by('id')
    
    if category_slug != None:
        categories = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=categories)
        
    # Sort dynamic filter
    sort_by = request.GET.get('sort')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_date')
        
    # Colors dynamic filter
    selected_colors = request.GET.getlist('color')
    if selected_colors:
        products = products.filter(variation__variation_category='color', variation__variation_value__iexact__in=selected_colors).distinct()
        
    # Sizes dynamic filter
    selected_sizes = request.GET.getlist('size')
    if selected_sizes:
        products = products.filter(variation__variation_category='size', variation__variation_value__in=selected_sizes).distinct()
        
    # Prices dynamic filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price and min_price != '0':
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
        
    product_count = products.count()
    paginator = Paginator(products, 9)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    
    # Build query string for pagination links (excluding page parameter)
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = query_params.urlencode()
    
    # Build active filters removal URLs list
    active_filters = []
    

        
    # 2. Search keyword filter tag
    if request.GET.get('keyword'):
        q_params = request.GET.copy()
        del q_params['keyword']
        base_url = request.path
        keyword_remove_url = f"{base_url}?{q_params.urlencode()}" if q_params.urlencode() else base_url
        active_filters.append({
            'type': 'keyword',
            'label': f'Search: "{request.GET.get("keyword")}"',
            'remove_url': keyword_remove_url,
        })
        
    # 3. Sizes filter tags
    for sz in selected_sizes:
        q_params = request.GET.copy()
        sizes_list = q_params.getlist('size')
        if sz in sizes_list:
            sizes_list.remove(sz)
        q_params.setlist('size', sizes_list)
        base_url = request.path
        size_remove_url = f"{base_url}?{q_params.urlencode()}" if q_params.urlencode() else base_url
        active_filters.append({
            'type': 'size',
            'label': f"Size: {sz}",
            'remove_url': size_remove_url,
        })
        
    # Colors filter tags
    for col in selected_colors:
        q_params = request.GET.copy()
        colors_list = q_params.getlist('color')
        if col in colors_list:
            colors_list.remove(col)
        q_params.setlist('color', colors_list)
        base_url = request.path
        color_remove_url = f"{base_url}?{q_params.urlencode()}" if q_params.urlencode() else base_url
        active_filters.append({
            'type': 'color',
            'label': f"Color: {col}",
            'remove_url': color_remove_url,
        })
        
    # Sort tag (if not default)
    if sort_by in ['price_low', 'price_high', 'newest']:
        q_params = request.GET.copy()
        del q_params['sort']
        base_url = request.path
        sort_remove_url = f"{base_url}?{q_params.urlencode()}" if q_params.urlencode() else base_url
        
        sort_label = "Price: Low to High" if sort_by == 'price_low' else ("Price: High to Low" if sort_by == 'price_high' else "Newest")
        active_filters.append({
            'type': 'sort',
            'label': f"Sort: {sort_label}",
            'remove_url': sort_remove_url,
        })
        
    # 4. Price range filter tag
    if (min_price and min_price != '0') or max_price:
        q_params = request.GET.copy()
        if 'min_price' in q_params:
            del q_params['min_price']
        if 'max_price' in q_params:
            del q_params['max_price']
        base_url = request.path
        price_remove_url = f"{base_url}?{q_params.urlencode()}" if q_params.urlencode() else base_url
        
        min_p_val = min_price if min_price else '0'
        max_p_val = max_price if max_price else '1000+'
        active_filters.append({
            'type': 'price',
            'label': f"Price: ₹{min_p_val} - ₹{max_p_val}",
            'remove_url': price_remove_url,
        })
        
    context = {
        'products': paged_products,
        'product_count' : product_count,
        'category': categories,
        'selected_sizes': selected_sizes,
        'selected_colors': selected_colors,
        'sort_by': sort_by,
        'min_price': min_price,
        'max_price': max_price,
        'query_string': query_string,
        'active_filters': active_filters,
    }
    return render(request, 'store/store.html', context)

def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=single_product).exists()
    except Exception as e:
        raise e
    if request.user.is_authenticated:
        try:
            orderproduct = OrderProduct.objects.filter(user=request.user, product_id=single_product.id).exists()
        except OrderProduct.DoesNotExist:
            orderproduct = None
    else:
        orderproduct = None


    reviews = ReviewRating.objects.filter(product_id=single_product.id, status=True)

    product_gallery = ProductGallery.objects.filter(product_id=single_product.id)
    
    # Get products from the same category (excluding current product)
    related_products = Product.objects.filter(category=single_product.category, is_available=True).exclude(id=single_product.id)[:4]
    
    # Calculate rounded display rating
    avg = single_product.averageReview()
    floor_val = int(avg)
    decimal = avg - floor_val
    if decimal < 0.3:
        display_rating = float(floor_val)
    elif decimal < 0.8:
        display_rating = float(floor_val) + 0.5
    else:
        display_rating = float(floor_val) + 1.0
        
    context = {
        'single_product': single_product,
        'in_cart'       : in_cart,
        'orderproduct': orderproduct,
        'reviews': reviews,
        'product_gallery': product_gallery,
        'related_products': related_products,
        'display_rating': display_rating,
    }

    return render(request, 'store/product_detail.html', context)
def search(request):
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.order_by('-created_date').filter(Q(description__icontains=keyword) | Q(product_name__icontains=keyword))
            product_count = products.count()
    context = {
        'products': products,
        'product_count': product_count,
    }
    return render(request, 'store/store.html', context)
def submit_review(request, product_id):
    url = request.META.get('HTTP_REFERER')
    if request.method == 'POST':
        try:
            reviews = ReviewRating.objects.get(user__id=request.user.id, product__id=product_id)
            form = ReviewForm(request.POST, instance=reviews)
            form.save()
            messages.success(request, 'Thanks for the review.')
            return redirect(url)
        except ReviewRating.DoesNotExist:
            form = ReviewForm(request.POST)
            if form.is_valid():
                data = ReviewRating()
                data.subject = form.cleaned_data['subject']
                data.rating = form.cleaned_data['rating']
                data.review = form.cleaned_data['review']
                data.ip = request.META.get('REMOTE_ADDR')
                data.product_id = product_id
                data.user_id = request.user.id
                data.save()
                messages.success(request, 'Thank you! Your review has been submitted.')
                return redirect(url)

def toggle_wishlist(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'login required'}, status=401)
        
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            product = Product.objects.get(id=product_id)
            wishlist_item, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
            if not created:
                wishlist_item.delete()
                return JsonResponse({'status': 'removed'})
            return JsonResponse({'status': 'added'})
        except Product.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Product not found'}, status=404)
    return JsonResponse({'status': 'error'}, status=400)

@login_required(login_url='login')
def wishlist_view(request):
    items = WishlistItem.objects.filter(user=request.user).order_by('-added_date')
    context = {'wishlist_items': items}
    return render(request, 'store/wishlist.html', context)
