from django.shortcuts import render, redirect,HttpResponse
from .models import Recipe, Product,RecipeIngredient,Order
from decimal import Decimal
from datetime import datetime
from django.contrib import messages
import logging
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from inventory.models import ProductBatch
from django.http import JsonResponse
from django.urls import reverse
from django.db import models
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from django.db.models import Sum, Count, Avg
from datetime import datetime, timedelta
from django.db.models.functions import ExtractHour
from user_auth.models import Staff
from django.contrib.auth.models import User


logger = logging.getLogger(__name__)

@login_required
def cashier_report(request):
    """
    Renders the cashier report page (GET).
    Also handles POST export_pdf action.
    """
    # POST: export PDF
    if request.method == 'POST' and request.POST.get('action') == 'export_pdf':
        date_range = request.POST.get('date_range', 'this_week')
        from_date = request.POST.get('from_date', '')
        to_date = request.POST.get('to_date', '')
        cashier_val = request.POST.get('cashier', 'all')

        orders = Order.objects.select_related('cashier').all()

        # Date filtering
        today = timezone.now().date()
        try:
            if date_range == 'today':
                orders = orders.filter(date_time__date=today)
            elif date_range == 'this_week':
                start_of_week = today - timedelta(days=today.weekday())
                orders = orders.filter(date_time__date__gte=start_of_week)
            elif date_range == 'this_month':
                start_of_month = today.replace(day=1)
                orders = orders.filter(date_time__date__gte=start_of_month)
            elif date_range == 'last_month':
                last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
                last_month_end = today.replace(day=1) - timedelta(days=1)
                orders = orders.filter(date_time__date__range=[last_month_start, last_month_end])
            elif date_range == 'custom' and from_date and to_date:
                f = datetime.strptime(from_date, '%Y-%m-%d').date()
                t = datetime.strptime(to_date, '%Y-%m-%d').date()
                orders = orders.filter(date_time__date__range=[f, t])
        except Exception as e:
            messages.error(request, "Invalid dates supplied for export.")
            return redirect('cashierReport')

        # Cashier filtering (safe)
        if cashier_val and cashier_val != 'all':
            if str(cashier_val).isdigit():
                orders = orders.filter(cashier__id=int(cashier_val))
            else:
                # if client sent username or something else, ignore or try to match - here we ignore
                pass

        # Build PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="cashier_report.pdf"'
        p = canvas.Canvas(response)
        p.setFont("Helvetica", 10)
        y = 800
        p.drawString(40, y, "Misosi Pluss++ Cashier Transaction Report")
        y -= 18
        p.drawString(40, y, f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        y -= 18
        p.drawString(40, y, f"Date Range: {date_range.replace('_', ' ').title()}")
        y -= 18
        if date_range == 'custom':
            p.drawString(40, y, f"From: {from_date} To: {to_date}")
            y -= 18

        if cashier_val == 'all':
            p.drawString(40, y, "Cashier: All")
        else:
            try:
                cashier_user = User.objects.get(id=int(cashier_val))
                p.drawString(40, y, f"Cashier: {cashier_user.get_full_name() or cashier_user.username}")
            except Exception:
                p.drawString(40, y, "Cashier: (unknown)")
        y -= 30

        # Table header
        p.drawString(40, y, "Order ID")
        p.drawString(140, y, "Date")
        p.drawString(260, y, "Cashier")
        p.drawString(380, y, "Amount")
        y -= 16
        p.line(40, y, 550, y)
        y -= 12

        total_amount = 0
        for order in orders:
            # items as string for PDF
            try:
                # Expect order.items to be a list of dicts like [{'name':'X','quantity':2}, ...]
                if isinstance(order.items, (list, tuple)):
                    items_str = ', '.join(f"{it.get('quantity', '')} x {it.get('name','')}" for it in order.items)
                else:
                    # if stored as string
                    items_str = str(order.items)
            except Exception:
                items_str = str(order.items)

            date_str = order.date_time.strftime('%Y-%m-%d %H:%M')
            cashier_name = order.cashier.get_full_name() if getattr(order, 'cashier', None) else 'Unknown'
            amount = float(order.total_amount or 0)
            total_amount += amount

            p.drawString(40, y, str(order.order_id))
            p.drawString(140, y, date_str)
            p.drawString(260, y, cashier_name)
            p.drawString(380, y, f"{amount:.2f} Tsh")
            y -= 16

            # print items on next line if needed
            if y < 80:
                p.showPage()
                p.setFont("Helvetica", 10)
                y = 800

        # Footer totals
        y -= 10
        p.line(40, y, 550, y)
        y -= 16
        p.drawString(40, y, f"Total Orders: {orders.count()}")
        p.drawString(200, y, f"Total Revenue: {total_amount:.2f} Tsh")

        p.showPage()
        p.save()
        return response

    # GET: render page with cashier dropdown
    orders = Order.objects.select_related('cashier').all().order_by('-date_time')[:200]  # initial few records
    cashiers = Staff.objects.filter(role='Cashier').select_related('user')
    return render(request, 'customer/cashier_report.html', {'orders': orders, 'cashiers': cashiers})


@login_required
def search_cashier_report(request):
    """
    AJAX endpoint: returns JSON with:
      - orders: list of orders (order_id, date_time, cashier, items string, total_amount)
      - total_revenue, total_orders
      - revenue_by_day: [{date, revenue}, ...]
    """
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    date_range = request.GET.get('date_range', 'this_week')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    cashier_val = request.GET.get('cashier', 'all')

    orders_qs = Order.objects.select_related('cashier').all()

    # Date filtering
    today = timezone.now().date()
    try:
        if date_range == 'today':
            orders_qs = orders_qs.filter(date_time__date=today)
        elif date_range == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            orders_qs = orders_qs.filter(date_time__date__gte=start_of_week)
        elif date_range == 'this_month':
            start_of_month = today.replace(day=1)
            orders_qs = orders_qs.filter(date_time__date__gte=start_of_month)
        elif date_range == 'last_month':
            last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            last_month_end = today.replace(day=1) - timedelta(days=1)
            orders_qs = orders_qs.filter(date_time__date__range=[last_month_start, last_month_end])
        elif date_range == 'custom' and from_date and to_date:
            f = datetime.strptime(from_date, '%Y-%m-%d').date()
            t = datetime.strptime(to_date, '%Y-%m-%d').date()
            orders_qs = orders_qs.filter(date_time__date__range=[f, t])
    except Exception:
        return JsonResponse({'error': 'Invalid date filter'}, status=400)

    # Cashier filtering (safe)
    if cashier_val and cashier_val != 'all':
        if str(cashier_val).isdigit():
            orders_qs = orders_qs.filter(cashier__id=int(cashier_val))
        else:
            # try matching by username (optional)
            orders_qs = orders_qs.filter(cashier__username=cashier_val)

    # Build totals and revenue_by_day
    total_revenue = float(orders_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or 0)
    total_orders = orders_qs.count()

    revenue_by_day = {}
    for o in orders_qs:
        day = o.date_time.date().isoformat()
        revenue_by_day[day] = revenue_by_day.get(day, 0) + float(o.total_amount or 0)

    revenue_by_day_list = [{'date': d, 'revenue': revenue_by_day[d]} for d in sorted(revenue_by_day.keys())]

    # List orders to return
    orders_list = []
    for o in orders_qs.order_by('-date_time')[:500]:  # limit to 500 to avoid huge payloads
        # safe items serialization
        try:
            if isinstance(o.items, (list, tuple)):
                items_str = ', '.join(f"{it.get('quantity','')} x {it.get('name','')}" for it in o.items)
            else:
                items_str = str(o.items)
        except Exception:
            items_str = str(o.items)

        orders_list.append({
            'order_id': o.order_id,
            'date_time': o.date_time.strftime('%Y-%m-%d %H:%M'),
            'cashier': (o.cashier.get_full_name() or o.cashier.username) if getattr(o, 'cashier', None) else 'Unknown',
            'items': items_str,
            'total_amount': float(o.total_amount or 0)
        })

    return JsonResponse({
        'orders': orders_list,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'revenue_by_day': revenue_by_day_list
    })




def register_recipe(request):
    products = Product.objects.all()
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        category = request.POST.get('category')
        price_str = request.POST.get('price')
        ingredient_ids = request.POST.getlist('ingredients[]')
        image = request.FILES.get('image')
        
        # Basic validation
        if not all([name, category, price_str]):
            return render(request, 'customer/add_recipe.html', {
                'products': products,
                'error': 'Required fields are missing.'
            })
        
        try:
            price = Decimal(price_str)
        except:
            return render(request, 'customer/add_recipe.html', {
                'products': products,
                'error': 'Invalid price format.'
            })
        
        # Validate quantities
        quantities = {}
        for product_id in ingredient_ids:
            quantity = request.POST.get(f'quantity_{product_id}')
            if not quantity:
                return render(request, 'customer/add_recipe.html', {
                    'products': products,
                    'error': 'Quantity missing for one or more ingredients.'
                })
            try:
                quantities[product_id] = Decimal(quantity)
            except:
                return render(request, 'customer/add_recipe.html', {
                    'products': products,
                    'error': 'Invalid quantity format.'
                })
        # Create recipe
        recipe = Recipe(
            name=name,
            description=description,
            category=category,
            price=price,
            image=image
        )
        recipe.full_clean()  # Validate model fields
        recipe.save()

                # Add ingredients with quantities and units
        for product_id in ingredient_ids:
            product = Product.objects.get(id=product_id)
            RecipeIngredient.objects.update_or_create(
                recipe=recipe,
                product=product,
                quantity=quantities[product_id],
                unit=product.unit
                )
        
        return redirect('recipe_management')  # Replace with your success URL, e.g., recipe list
        
    return render(request, 'customer/add_recipe.html', {'products': products})

def menu_view(request):
    recipes = Recipe.objects.filter(is_available=True)
    logger.debug(f"Recipes fetched for menu: {list(recipes.values('id', 'name', 'category', 'is_available', 'price', 'description', 'image'))}")
    
    if request.method == 'POST':
        logger.debug(f"POST data: {request.POST}")
        action = request.POST.get('action')
        
        if action == 'confirm_order':
            order_items = request.POST.getlist('order_items[]')
            try:
                order_details = []
                total = 0
                order_id = f"#ORD-{timezone.now().strftime('%Y%m%d')}-{Order.objects.count() + 1:03d}"

                for item in order_items:
                    recipe_id, quantity = item.split(':')
                    quantity = int(quantity)
                    if quantity <= 0:
                        continue

                    recipe = Recipe.objects.get(id=recipe_id)
                    recipe_ingredients = RecipeIngredient.objects.filter(recipe=recipe)

                    for ri in recipe_ingredients:
                        product = ri.product
                        required_quantity = ri.quantity * quantity

                        batches = ProductBatch.objects.filter(
                            product=product,
                            expiration_date__gte=timezone.now().date(),
                            quantity__gt=0
                        ).order_by('expiration_date')

                        for batch in batches:
                            if required_quantity <= 0:
                                break
                            if batch.quantity >= required_quantity:
                                batch.quantity -= required_quantity
                                batch.save()
                                required_quantity = 0
                            else:
                                required_quantity -= batch.quantity
                                batch.quantity = 0
                                batch.save()

                        if required_quantity > 0:
                            messages.error(request, f"Insufficient stock for {product.name} to fulfill {recipe.name} order.")
                            return render(request, 'customer/index.html', {'recipes': Recipe.objects.filter(is_available=True)})

                    item_total = recipe.price * quantity
                    total += item_total
                    order_details.append({
                        'recipe_id': recipe.id,
                        'name': recipe.name,
                        'quantity': quantity,
                        'item_total': float(item_total)
                    })

                if not request.user.is_authenticated:
                    messages.error(request, "Failed To Confirm Because You Have Not Login")
                    return redirect("userLogin") 

                # Save order to database
                Order.objects.create(
                    order_id=order_id,
                    cashier=request.user,
                    total_amount=total,
                    items=order_details
                )

                request.session['order_details'] = {
                    'items': order_details,
                    'total': float(total),
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'cashier': request.user.get_full_name() or request.user.username
                }
                messages.success(request, 'Order confirmed successfully.')
                return redirect('orderConfirmation')        

            except Exception as e:
                logger.error(f"Error confirming order: {str(e)}")
                messages.error(request, f'Failed to confirm order: {str(e)}')
        
        return render(request, 'customer/index.html', {'recipes': Recipe.objects.filter(is_available=True)})
    
    return render(request, 'customer/index.html', {'recipes': recipes})
@login_required
def order_confirmation(request):
    order_details = request.session.get('order_details')
    if not order_details:
        messages.error(request, 'No order details found.')
        return redirect('menu')
    
    if request.method == 'POST' and request.POST.get('action') == 'download_pdf':
        from reportlab.pdfgen import canvas
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="receipt.pdf"'

        p = canvas.Canvas(response)
        p.drawString(100, 800, "Misosi Pluss++ Receipt")
        p.drawString(100, 780, f"Date: {order_details['date']}")
        p.drawString(100, 760, f"Cashier: {order_details['cashier']}")

        y = 740
        for item in order_details['items']:
            p.drawString(100, y, f"{item['quantity']} x {item['name']} - {item['item_total']:.2f} Tsh")
            y -= 20

        p.drawString(100, y, f"Total: {order_details['total']:.2f} Tsh")
        p.save()
        return response

    return render(request, 'customer/order_confirmation.html', {
        'order_details': order_details,
        'messages': messages.get_messages(request)
    })

def recipe_view(request):
    return render(request, 'customer/edit_recipe.html')

@login_required
def recipe_management(request):
    recipes = Recipe.objects.all()
    category_choices = Recipe.CATEGORY_CHOICES  # <-- pass choices
    return render(request, 'customer/recipe_view.html', {
        'recipes': recipes,
        'category_choices': category_choices
    })

@login_required
def search_recipes(request):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    search_query = request.GET.get('search', '').strip()
    category = request.GET.get('category', '')
    availability = request.GET.get('availability', '')

    recipes = Recipe.objects.all()

    # Apply filters
    if search_query:
        recipes = recipes.filter(
            models.Q(name__icontains=search_query) |
            models.Q(description__icontains=search_query)
        )

    if category:
        recipes = recipes.filter(category=category)

    if availability:
        is_available = availability.lower() == 'available'
        recipes = recipes.filter(is_available=is_available)

    # Prepare response data
    data = []
    placeholder_image = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23fdecd6'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='central' text-anchor='middle' font-family='monospace' font-size='14px' fill='%23e8731e'%3EImg%3C/text%3E%3C/svg%3E"
    
    for recipe in recipes:
        image_url = recipe.image.url if recipe.image else placeholder_image
        data.append({
            'id': recipe.id,
            'name': recipe.name,
            'description': recipe.description,
            'category': recipe.category,
            'price': str(recipe.price),
            'is_available': recipe.is_available,
            'image_url': image_url,
            'edit_url': reverse('edit_recipe', args=[recipe.id]),
            'delete_url': reverse('delete_recipe', args=[recipe.id])
        })

    return JsonResponse({'recipes': data})

@login_required
def edit_recipe(request, recipe_id):
    recipe = Recipe.objects.get(id=recipe_id)
    products = Product.objects.all()
    category_choices = Recipe.CATEGORY_CHOICES  # pass choices to template

    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            category = request.POST.get('category')
            price_str = request.POST.get('price')
            is_available = request.POST.get('is_available') == 'on'
            image = request.FILES.get('image')

            if not all([name, category, price_str]):
                messages.error(request, "Please fill in all required fields.")
                return render(request, 'customer/edit_recipe.html', {'recipe': recipe, 'products': products})

            try:
                price = Decimal(price_str)
            except:
                messages.error(request, "Invalid price format.")
                return render(request, 'customer/edit_recipe.html', {'recipe': recipe, 'products': products})

            recipe.name = name
            recipe.description = description
            recipe.category = category
            recipe.price = price
            recipe.is_available = is_available
            if image:
                recipe.image = image
            recipe.save()

            messages.success(request, "Recipe updated successfully!")
            return redirect('recipe_management')

        except Exception as e:
            logger.error(f"Error updating recipe: {str(e)}")
            messages.error(request, f"Error updating recipe: {str(e)}")
            return render(request, 'customer/edit_recipe.html', {'recipe': recipe, 'products': products})

    return render(request, 'customer/edit_recipe.html', {
        'recipe': recipe,
        'products': products,
        'category_choices': category_choices
    })
@login_required
def delete_recipe(request, recipe_id):
    if request.method == 'POST':
        try:
            recipe = Recipe.objects.get(id=recipe_id)
            recipe.delete()
            messages.success(request, "Recipe deleted successfully!")
        except Exception as e:
            logger.error(f"Error deleting recipe: {str(e)}")
            messages.error(request, f"Error deleting recipe: {str(e)}")
        return redirect('recipe_management')
    return redirect('recipe_management')

def cashier_report(request):
    return render(request,'customer/cashier_report.html')