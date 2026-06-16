from django.shortcuts import render, redirect,HttpResponse
from .models import Recipe, Product,RecipeIngredient,Order
from decimal import Decimal
from datetime import datetime
from django.contrib import messages
import logging
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from inventory.models import ProductBatch, InventoryTransaction
from django.http import JsonResponse
from django.urls import reverse
from django.db import models, transaction as db_transaction
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from django.db.models import Sum, Count, Avg
from datetime import datetime, timedelta
from django.db.models.functions import ExtractHour
from user_auth.models import Staff
from django.contrib.auth.models import User
logger = logging.getLogger(__name__)
from django.template.loader import render_to_string
from weasyprint import HTML


@login_required
def cashier_report(request):
    """
    Renders the cashier report page or handles PDF export.
    """
    today = timezone.now().date()

    # -------------------- PDF EXPORT --------------------
    if request.method == 'GET' and request.GET.get('action') == 'export_pdf':
        print("PDF EXPORT TRIGGERED ✅")

        date_range = request.GET.get('date_range', 'this_week')
        from_date = request.GET.get('from_date', '')
        to_date = request.GET.get('to_date', '')
        cashier_val = request.GET.get('cashier', 'all')

        orders = filter_orders(date_range, from_date, to_date, cashier_val)

        # Retrieve cashier name safely
        cashier_name = "All Cashiers"
        if cashier_val != "all" and str(cashier_val).isdigit():
            try:
                cashier_user = User.objects.get(id=int(cashier_val))
                cashier_name = cashier_user.get_full_name() or cashier_user.username
            except User.DoesNotExist:
                pass

        # Prepare orders list formatted specifically for the PDF template to avoid dictionary lookup/JSON rendering issues
        orders_list = []
        for order in orders:
            try:
                if isinstance(order.items, (list, tuple)):
                    items_str = ', '.join(f"{it.get('quantity', '')} x {it.get('name', '')}" for it in order.items)
                else:
                    items_str = str(order.items)
            except Exception:
                items_str = str(order.items)

            orders_list.append({
                'order_id': order.order_id,
                'date_time': order.date_time,
                'cashier_name': (order.cashier.get_full_name() or order.cashier.username) if getattr(order, 'cashier', None) else 'Unknown',
                'items': items_str,
                'total_amount': order.total_amount,
            })

        html = render_to_string(
            "customer/cashier_report_pdf.html",
            {
                "orders": orders_list,
                "total_orders": len(orders_list),
                "total_revenue": sum(o.total_amount or 0 for o in orders),
                "date_range": date_range.replace('_', ' ').title(),
                "cashier_name": cashier_name,
            }
        )

        pdf = HTML(
            string=html,
            base_url=request.build_absolute_uri()
        ).write_pdf()

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="cashier_report.pdf"'
        return response  # ✅ Must return here to actually send PDF

    # -------------------- GET: Render normal page --------------------
    orders = Order.objects.select_related('cashier').order_by('-date_time')[:200]
    cashiers = Staff.objects.filter(role='Cashier').select_related('user')

    cashier_list = [
        {'id': c.user.id, 'name': c.user.get_full_name() or c.user.username}
        for c in cashiers
    ]

    return render(request, 'customer/cashier_report.html', {
        'orders': orders,
        'cashiers': cashier_list,
    })

def filter_orders(date_range, from_date, to_date, cashier_val):
    orders = Order.objects.select_related('cashier').all()
    today = timezone.now().date()

    if date_range == 'today':
        orders = orders.filter(date_time__date=today)

    elif date_range == 'this_week':
        start_of_week = today - timedelta(days=today.weekday())
        orders = orders.filter(date_time__date__gte=start_of_week)

    elif date_range == 'this_month':
        orders = orders.filter(date_time__date__gte=today.replace(day=1))

    elif date_range == 'last_month':
        last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_month_end = today.replace(day=1) - timedelta(days=1)
        orders = orders.filter(date_time__date__range=[last_month_start, last_month_end])

    elif date_range == 'custom' and from_date and to_date:
        f = datetime.strptime(from_date, '%Y-%m-%d').date()
        t = datetime.strptime(to_date, '%Y-%m-%d').date()
        orders = orders.filter(date_time__date__range=[f, t])

    if cashier_val != 'all' and str(cashier_val).isdigit():
        orders = orders.filter(cashier__id=int(cashier_val))

    return orders


@login_required
def search_cashier_report(request):
    """
    AJAX endpoint to fetch cashier report data.
    Returns JSON containing:
      - orders
      - total_revenue
      - total_orders
      - revenue_by_day
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    date_range = request.GET.get('date_range', 'this_week')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    cashier_val = request.GET.get('cashier', 'all')

    orders_qs = filter_orders(date_range, from_date, to_date, cashier_val)
    today = timezone.now().date()

    # ------------------ Date filtering ------------------
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

    # ------------------ Cashier filter ------------------
    if cashier_val and cashier_val != 'all':
        if str(cashier_val).isdigit():
            orders_qs = orders_qs.filter(cashier__id=int(cashier_val))
        else:
            orders_qs = orders_qs.filter(cashier__username__iexact=cashier_val)

    # ------------------ Totals ------------------
    total_revenue = float(orders_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or 0)
    total_orders = orders_qs.count()

    # ------------------ Revenue by day ------------------
    revenue_by_day = {}
    for order in orders_qs:
        day = order.date_time.date().isoformat()
        revenue_by_day[day] = revenue_by_day.get(day, 0) + float(order.total_amount or 0)

    revenue_by_day_list = [
        {'date': d, 'revenue': revenue_by_day[d]} for d in sorted(revenue_by_day.keys())
    ]

    # ------------------ Orders list ------------------
    orders_list = []
    for order in orders_qs.order_by('-date_time')[:500]:
        try:
            if isinstance(order.items, (list, tuple)):
                items_str = ', '.join(f"{it.get('quantity', '')} x {it.get('name', '')}" for it in order.items)
            else:
                items_str = str(order.items)
        except Exception:
            items_str = str(order.items)

        orders_list.append({
            'order_id': order.order_id,
            'date_time': order.date_time.strftime('%Y-%m-%d %H:%M'),
            'cashier': (order.cashier.get_full_name() or order.cashier.username) if getattr(order, 'cashier', None) else 'Unknown',
            'items': items_str,
            'total_amount': float(order.total_amount or 0),
        })

    return JsonResponse({
        'orders': orders_list,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'revenue_by_day': revenue_by_day_list,
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

            if not request.user.is_authenticated:
                messages.error(request, "Failed To Confirm Because You Have Not Login")
                return redirect("userLogin")

            try:
                with db_transaction.atomic():
                    order_details = []
                    total = 0
                    order_id = f"#ORD-{timezone.now().strftime('%Y%m%d')}-{Order.objects.count() + 1:03d}"

                    # Resolve staff profile for transaction logging
                    staff_profile = None
                    if hasattr(request.user, 'staff_profile'):
                        staff_profile = request.user.staff_profile

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
                            total_needed = required_quantity  # track for error msg

                            batches = ProductBatch.objects.select_for_update().filter(
                                product=product,
                                expiration_date__gte=timezone.now().date(),
                                quantity__gt=0
                            ).order_by('expiration_date')  # FEFO

                            for batch in batches:
                                if required_quantity <= 0:
                                    break

                                if batch.quantity >= required_quantity:
                                    deducted = required_quantity
                                    batch.quantity -= required_quantity
                                    batch.save()
                                    required_quantity = 0
                                else:
                                    deducted = batch.quantity
                                    required_quantity -= batch.quantity
                                    batch.quantity = 0
                                    batch.save()

                                # ✅ Log a Stock Out transaction for each batch deduction
                                InventoryTransaction.objects.create(
                                    batch=batch,
                                    transaction_type='Stock Out',
                                    quantity=deducted,
                                    unit_price=batch.price,
                                    staff=staff_profile,
                                    notes=f"Order {order_id}: {quantity} x {recipe.name}"
                                )

                            if required_quantity > 0:
                                raise ValueError(
                                    f"Insufficient stock for '{product.name}' "
                                    f"(needed {total_needed} {product.unit}, "
                                    f"short by {required_quantity} {product.unit}) "
                                    f"to fulfill '{recipe.name}' order."
                                )

                        item_total = recipe.price * quantity
                        total += item_total
                        order_details.append({
                            'recipe_id': recipe.id,
                            'name': recipe.name,
                            'quantity': quantity,
                            'item_total': float(item_total)
                        })

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

            except ValueError as e:
                # Insufficient stock — no DB changes committed (atomic rollback)
                messages.error(request, str(e))
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