from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.text import slugify
from store.models import Product
from category.models import Category
from .forms import RegisterationForm, UserForm, UserProfileForm
from .models import Account, UserProfile
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, Q
from django.views.decorators.http import require_POST
from orders.models import Order, OrderProduct
from orders.tracking import record_tracking_event

#Verification email
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage


from carts.views import _cart_id
from carts.models import Cart, CartItem
import requests
from urllib.parse import urlparse, parse_qs
# Create your views here.
def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            username = email.split("@")[0]        
            user = Account.objects.create_user(first_name=first_name, last_name=last_name, email=email,username=username, password=password)
            user.phone_number = phone_number
            user.save()

            # UserProfile is created by post_save signal in accounts.models

            #USER ACTIVATION
            current_site = get_current_site(request)
            mail_subject = 'Please activate your account'
            message = render_to_string('accounts/account_verification_email.html', {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            try:
                send_email.send()
                #messages.success(request, 'We have sent you a verfication mail. Please verify to continue.')
                return redirect('/accounts/login/?command=verification&email='+email)
            except Exception as e:
                # Bypass verification if SMTP fails in local/sandbox
                user.is_active = True
                user.save()
                messages.warning(request, 'Account created and automatically activated (SMTP email delivery failed). You may log in now.')
                return redirect('login')
    else:
        form = RegisterationForm()
    context = {
            'form': form,
    }
    return render(request, 'accounts/register.html', context)

def login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = auth.authenticate(email=email, password=password)

        if user is not None:
            try:
                cart = Cart.objects.get(cart_id=_cart_id(request))
                is_cart_item_exists = CartItem.objects.filter(cart=cart).exists()
                if is_cart_item_exists:
                    cart_item = CartItem.objects.filter(cart=cart)
                    
                    product_variation = []
                    for item in cart_item:
                        variation = item.variations.all()
                        product_variation.append(list(variation))

                    cart_item = CartItem.objects.filter(user=user)
                    ex_var_list = []
                    id = []
                    for item in cart_item:
                        existing_variation = item.variations.all()
                        ex_var_list.append(list(existing_variation))
                        id.append(item.id)

                    for pr in product_variation:
                        if pr in ex_var_list:
                            index = ex_var_list.index(pr)
                            item_id = id[index]
                            item = CartItem.objects.get(id=item_id)
                            item.quantity += 1
                            item.user = user
                            item.save()
                        else:
                            cart_item = CartItem.objects.filter(cart=cart)
                            for item in cart_item:
                                item.user = user
                                item.save()
                    #for item in cart_item:
                        #item.user = user
                        #item.save()
            except:
                pass
            auth.login(request, user)
            messages.success(request, 'You are now logged in.')
            url = request.META.get('HTTP_REFERER')
            try:
                if url:
                    query = urlparse(url).query
                    # next=/cart/checkout/
                    params = parse_qs(query)
                    next_page = params.get('next', [None])[0]
                    if next_page:
                        return redirect(next_page)
                return redirect('dashboard')
            except Exception:
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid login credentials')
            return redirect('login')
    return render(request, 'accounts/login.html')


@login_required(login_url = 'login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'You are logged out.')
    return redirect('login')

def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Thank You for Registering with us! Your account is activated, Happy Shopping!!')
        return redirect('login')
    
    else:
        messages.error(request, 'Invalid activation link')
        return redirect('register')

@login_required(login_url='login')
def dashboard(request):
    orders = Order.objects.order_by('-created_at').filter(user_id=request.user.id, is_ordered=True)
    orders_count = orders.count()

    # Safely get or create a user profile
    userprofile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Handling for profile picture
    if userprofile.profile_picture and hasattr(userprofile.profile_picture, 'url'):
        profile_pic_url = userprofile.profile_picture.url
    else:
        profile_pic_url = None  # or provide a default image URL

    context = {
        'orders_count': orders_count,
        'userprofile': userprofile,
        'profile_pic_url': profile_pic_url,  # Include this in context to use in the template
    }

    return render(request, 'accounts/dashboard.html', context)

def forgotPassword(request):
    if request.method == 'POST':
        email = request.POST['email']
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__exact=email)
            #Reset Password email
            current_site = get_current_site(request)
            mail_subject = 'Reset Your Password'
            message = render_to_string('accounts/reset_password_email.html', {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            
            try:
                send_email.send()
                messages.success(request, 'Password Reset mail sent to your email. You can now change your Password.')
            except Exception as e:
                # For development: show the reset link directly
                reset_url = f"http://{current_site}{reverse('resetpassword_validate', args=[urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)])}"
                messages.warning(request, f'Email could not be sent due to SMTP configuration. Please use this link to reset your password: {reset_url}')
            
            return redirect('login')
        else:
            messages.error(request, 'Account does not Exist')
            return redirect('forgotPassword')
    return render(request, 'accounts/forgotPassword.html')

def resetpassword_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.success(request, 'Please reset your Password')
        return redirect('resetPassword')
    else:
        messages.error(request, 'This link has been expired!')
        return redirect('login')

    
def resetPassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request, 'Password reset successful')
            return redirect('login')
        else:
            messages.error(request, 'Password does not match')
            return redirect('resetPassword')
    else:
        return render(request, 'accounts/resetPassword.html')

@login_required(login_url='login')    
def my_orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    selected_order_number = request.GET.get('order')
    selected_order = orders.filter(order_number=selected_order_number).first() if selected_order_number else orders.first()
    selected_order_products = []
    tracking_steps = []

    if selected_order:
        selected_order_products = OrderProduct.objects.filter(order=selected_order).select_related('product')
        for order in orders:
            first_item = OrderProduct.objects.filter(order=order).select_related('product').first()
            order.primary_product_name = first_item.product.product_name if first_item else 'Nexuskart order'
            order.primary_product_category = first_item.product.category.category_name if first_item and first_item.product.category else 'Order'

        status = 'Delivered' if selected_order.status == 'Completed' else selected_order.status
        steps = [
            ('New', 'Order placed', 'We received your order.'),
            ('Accepted', 'Accepted', 'Your order has been confirmed.'),
            ('Shipped', 'Shipped', 'Your package is on the way.'),
            ('Delivered', 'Delivered', "Enjoy. It's yours."),
        ]
        current_index = next((index for index, step in enumerate(steps) if step[0] == status), 0)

        if status == 'Cancelled':
            tracking_steps = [{
                'label': 'Order cancelled',
                'description': 'This order was cancelled.',
                'state': 'cancelled',
            }]
        else:
            events_by_status = {
                event.status: event
                for event in selected_order.tracking_events.all()
            }
            tracking_steps = [
                {
                    'label': label,
                    'description': description,
                    'state': 'done' if index <= current_index else 'pending',
                    'is_current': index == current_index,
                    'event': events_by_status.get(step_status),
                }
                for index, (step_status, label, description) in enumerate(steps)
            ]

    context = {
        'orders' : orders,
        'selected_order': selected_order,
        'selected_order_products': selected_order_products,
        'tracking_steps': tracking_steps,
    }
    return render(request, 'accounts/my_orders.html', context)

@login_required(login_url='login')
@require_POST
def request_order_cancellation(request):
    order_number = request.POST.get('order_number')
    if not order_number:
        messages.error(request, 'Order number is required.')
        return redirect('my_orders')

    try:
        order = Order.objects.get(order_number=order_number, user=request.user)
        if order.status in ['Cancelled', 'Completed', 'Delivered']:
            messages.error(request, f'Order {order_number} cannot be cancelled at this stage.')
        else:
            order.cancellation_requested = True
            order.save()
            messages.success(request, f'Cancellation requested for order {order_number}. Our team will review it shortly.')
    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')

    return redirect(f"{reverse('my_orders')}?order={order_number}")
@login_required(login_url='login')
def edit_profile(request):
    userprofile, created = UserProfile.objects.get_or_create(user=request.user)  # Use get_or_create to handle missing profiles
    if created:
        messages.info(request, 'Profile was created. Please update your profile information.')  # Optional: Inform the user that a profile was created

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=userprofile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('edit_profile')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=userprofile)
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'userprofile': userprofile,
    }
    return render(request, 'accounts/edit_profile.html', context)

@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST['current_password']
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']

        user = Account.objects.get(username__exact=request.user.username)

        if new_password == confirm_password:
            success = user.check_password(current_password)
            if success:
                user.set_password(new_password)
                user.save()
                # auth.logout(request)
                messages.success(request, 'Password updated successfully.')
                return redirect('change_password')
            else:
                messages.error(request, 'Please enter valid current password')
                return redirect('change_password')
        else:
            messages.error(request, 'Password does not match!')
            return redirect('change_password')
    return render(request, 'accounts/change_password.html')

@login_required(login_url='login')
def order_detail(request, order_id):
    order_detail = OrderProduct.objects.filter(order__order_number=order_id)
    order = Order.objects.get(order_number=order_id)
    subtotal = 0
    for i in order_detail:
        subtotal += i.product_price * i.quantity

    context = {
        'order_detail': order_detail,
        'order': order,
        'subtotal': subtotal,
    }
    return render(request, 'accounts/order_detail.html', context)

@login_required(login_url='login')
def onboarding(request):
    if request.method == 'POST':
        # Check if user clicked Skip
        if 'skip' in request.POST:
            request.session['skip_onboarding'] = True
            return redirect('home')

        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            request.session['skip_onboarding'] = True
            messages.success(request, 'Your profile has been updated.')
            return redirect('store')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=request.user.userprofile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'accounts/onboarding.html', context)


@login_required(login_url='login')
def admin_dashboard(request):
    # Staff protection
    if not request.user.is_staff:
        return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

    # Card Statistics Queries
    total_orders = Order.objects.filter(is_ordered=True).count()
    
    total_revenue_dict = Order.objects.filter(is_ordered=True).aggregate(Sum('order_total'))
    total_revenue = total_revenue_dict['order_total__sum'] or 0
    
    pending_orders = Order.objects.filter(is_ordered=True, status__in=['New', 'Accepted']).count()
    
    total_customers = Account.objects.count()

    # Filtering/Searching for Recent Orders Table
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')
    
    recent_orders = Order.objects.filter(is_ordered=True)
    
    if status_filter == 'cancellation_requested':
        recent_orders = recent_orders.filter(cancellation_requested=True).exclude(status__in=['Cancelled', 'Completed'])
    elif status_filter != 'all':
        recent_orders = recent_orders.filter(status__iexact=status_filter)
        
    if query:
        recent_orders = recent_orders.filter(
            Q(order_number__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
        
    recent_orders = recent_orders.order_by('-created_at')

    # Paginate the orders: 8 orders per page
    paginator = Paginator(recent_orders, 8)
    page_num = request.GET.get('page')
    try:
        paginated_orders = paginator.page(page_num)
    except PageNotAnInteger:
        paginated_orders = paginator.page(1)
    except EmptyPage:
        paginated_orders = paginator.page(paginator.num_pages)

    # Prepopulate the primary product info for orders to display in the table
    for order in paginated_orders:
        first_item = OrderProduct.objects.filter(order=order).select_related('product').first()
        order.primary_product_name = first_item.product.product_name if first_item else 'Nexuskart order'
        order.primary_product_qty = first_item.quantity if first_item else 1

    # Low Stock Products Query (stock <= 5)
    from store.models import Product
    low_stock_products = Product.objects.filter(stock__lte=5).order_by('stock')

    # Top Selling Products Query (Top 5 based on OrderProduct quantity)
    top_selling_products = OrderProduct.objects.filter(order__is_ordered=True)\
        .values('product__product_name', 'product__price', 'product__id', 'product__images')\
        .annotate(total_sold=Sum('quantity'))\
        .order_by('-total_sold')[:5]

    # Notification Area: Pending "New" Orders
    new_orders_pending = Order.objects.filter(is_ordered=True, status='New').order_by('-created_at')
    
    # Cancellation requests
    cancellation_requests = Order.objects.filter(cancellation_requested=True).exclude(status__in=['Cancelled', 'Completed']).order_by('-updated_at')

    # Status Options for dropdowns (excluding 'New' as it is a transient/automatic state)
    status_options = ['Accepted', 'Shipped', 'Delivered', 'Cancelled']

    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'pending_orders': pending_orders,
        'total_customers': total_customers,
        'recent_orders': paginated_orders,
        'paginated_orders': paginated_orders,
        'low_stock_products': low_stock_products,
        'top_selling_products': top_selling_products,
        'new_orders_pending': new_orders_pending,
        'cancellation_requests': cancellation_requests,
        'status_options': status_options,
        'query': query,
        'status_filter': status_filter,
    }
    return render(request, 'accounts/admin_dashboard.html', context)


@login_required(login_url='login')
@require_POST
def admin_dashboard_update_status(request):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    order_id = request.POST.get('order_id')
    new_status = request.POST.get('status')

    order = get_object_or_404(Order, id=order_id)
    
    # Block modifying already cancelled orders
    if order.status == 'Cancelled':
        return JsonResponse({'success': False, 'error': 'Cancelled orders cannot be modified.'}, status=400)
    
    # Capitalize status appropriately to match STATUS_CHOICES
    valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
    formatted_status = new_status.capitalize() if new_status else ''
    
    if formatted_status == 'New':
        formatted_status = 'New'
    elif formatted_status == 'Cancel' or formatted_status == 'Cancelled':
        formatted_status = 'Cancelled'
    elif formatted_status == 'Accept' or formatted_status == 'Accepted':
        formatted_status = 'Accepted'
    elif formatted_status == 'Ship' or formatted_status == 'Shipped':
        formatted_status = 'Shipped'
    elif formatted_status == 'Deliver' or formatted_status == 'Delivered':
        formatted_status = 'Delivered'
    elif formatted_status == 'Complete' or formatted_status == 'Completed':
        formatted_status = 'Completed'

    if formatted_status in valid_statuses:
        order.status = formatted_status
        order.save()
        
        # Record tracking event
        record_tracking_event(order, formatted_status, request.user)
        
        return JsonResponse({
            'success': True, 
            'message': f'Order {order.order_number} status updated to {formatted_status}.'
        })
    else:
        return JsonResponse({'success': False, 'error': f'Invalid status: {new_status}'}, status=400)


@login_required(login_url='login')
def admin_order_detail(request, order_id):
    # Staff protection
    if not request.user.is_staff:
        return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

    # Get the order (by ID)
    order = get_object_or_404(Order, id=order_id)
    
    # Get products for this order
    order_detail = OrderProduct.objects.filter(order=order).select_related('product')
    
    subtotal = 0
    for item in order_detail:
        subtotal += item.product_price * item.quantity

    # Determine status flow for stepper (New -> Accepted -> Shipped -> Delivered)
    status_tone = {
        'New': 'bg-foreground text-background font-bold border border-foreground',
        'Accepted': 'bg-primary/10 text-primary border border-primary/20',
        'Shipped': 'bg-accent/15 text-accent border border-accent/30',
        'Delivered': 'bg-emerald-50 text-emerald-800 border border-emerald-200',
        'Completed': 'bg-emerald-50 text-emerald-800 border border-emerald-200',
        'Cancelled': 'bg-destructive/15 text-destructive border border-destructive/20',
    }
    
    status_options = ['New', 'Accepted', 'Shipped', 'Delivered', 'Cancelled']
    
    current_status = 'Delivered' if order.status == 'Completed' else order.status
    
    # Calculate progress width for stepper
    status_flow = ['New', 'Accepted', 'Shipped', 'Delivered']
    try:
        current_idx = status_flow.index(current_status)
    except ValueError:
        current_idx = -1  # if Cancelled or other status not in standard flow

    # Get tracking events
    tracking_events = order.tracking_events.all().order_by('created_at')

    context = {
        'order': order,
        'order_detail': order_detail,
        'subtotal': subtotal,
        'status_tone': status_tone.get(order.status, 'bg-secondary text-foreground border-border'),
        'current_status': current_status,
        'current_idx': current_idx,
        'status_flow': status_flow,
        'status_options': status_options,
        'tracking_events': tracking_events,
    }
    return render(request, 'accounts/admin_order_detail.html', context)

@login_required(login_url='login')
def admin_manage_inventory(request):
    if not request.user.is_superadmin:
        return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
    
    if request.method == 'POST':
        # Bulk save logic
        for key, value in request.POST.items():
            if key.startswith('stock_'):
                try:
                    product_id = int(key.split('_')[1])
                    new_stock = int(value)
                    product = Product.objects.get(id=product_id)
                    product.stock = new_stock
                    product.save()
                except (ValueError, Product.DoesNotExist):
                    continue
        messages.success(request, 'Inventory updated successfully.')
        return redirect(request.META.get('HTTP_REFERER', 'admin_manage_inventory'))
        
    products_list = Product.objects.all().order_by('-modified_date')
    
    paginator = Paginator(products_list, 10) # 10 products per page
    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
        
    context = {
        'products': products,
    }
    return render(request, 'accounts/admin_manage_inventory.html', context)

@login_required(login_url='login')
def admin_add_product(request):
    if not request.user.is_superadmin:
        return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
        
    if request.method == 'POST':
        product_name = request.POST.get('product_name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        category_id = request.POST.get('category')
        is_available = request.POST.get('is_available') == 'on'
        
        # Handle file upload
        images = request.FILES.get('images')
        
        try:
            category = Category.objects.get(id=category_id)
            slug = slugify(product_name)
            
            # Ensure slug is unique
            base_slug = slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
                
            Product.objects.create(
                product_name=product_name,
                slug=slug,
                description=description,
                price=price,
                stock=stock,
                category=category,
                is_available=is_available,
                images=images
            )
            messages.success(request, 'Product added successfully.')
            return redirect('admin_manage_inventory')
        except Exception as e:
            messages.error(request, f'Error adding product: {str(e)}')
            
    categories = Category.objects.all()
    context = {
        'categories': categories,
    }
    return render(request, 'accounts/admin_add_product.html', context)
