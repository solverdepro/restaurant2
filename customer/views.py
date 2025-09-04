from django.shortcuts import render, redirect,HttpResponse
from .models import Recipe, Product,RecipeIngredient
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime
from django.contrib import messages
import logging
from django.contrib.auth.decorators import login_required


logger = logging.getLogger(__name__)
# def home(request):
#     return render(request,'customer/index.html')

def admin_dashboard(request):
    return render(request,'customer/admin_dashboard.html')


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
        
        return redirect('admindashboard')  # Replace with your success URL, e.g., recipe list
        
    return render(request, 'customer/add_recipe.html', {'products': products})

def menu_view(request):
    recipes = Recipe.objects.filter(is_available=True)
    logger.debug(f"Recipes fetched for menu: {list(recipes.values('id', 'name', 'category', 'is_available', 'price', 'description', 'image'))}")
    
    if request.method == 'POST':
        logger.debug(f"POST data: {request.POST}")
        action = request.POST.get('action')
        
        if action == 'confirm_order':
            order_items = request.POST.getlist('order_items[]')  # Format: recipe_id:quantity
            try:
                #Validate and update inventory
                order_details = []
                total = 0
                for item in order_items:
                    recipe_id, quantity = item.split(':')
                    quantity = int(quantity)
                    if quantity <= 0:
                        continue
                    
                    recipe = Recipe.objects.get(id=recipe_id)
                    recipe_ingredients = RecipeIngredient.objects.filter(recipe=recipe)
                    
                    # Check and update ingredient quantities
                    for ri in recipe_ingredients:
                        product = ri.product
                        required_quantity = ri.quantity * quantity
                        if product.quantity < required_quantity:
                            messages.error(request, f"Insufficient stock for {product.name} to fulfill {recipe.name} order.")
                            return render(request, 'customer/index.html', {'recipes': Recipe.objects.filter(is_available=True)})
                        
                        product.quantity -= required_quantity
                        product.save()
                                # Store order details for confirmation page
                    item_total = recipe.price * quantity
                    total += item_total
                    order_details.append({
                        'recipe_id': recipe.id,
                        'name': recipe.name,
                        'quantity': quantity,
                        'item_total': float(item_total)
                    })
                
                # Store order details in session
                         # ✅ check authentication first
                    if not request.user.is_authenticated:
                             messages.error(request, "Failed To Confirm Because You Have Not Login")
                             return redirect("userLogin") 

                request.session['order_details'] = {
                    'items': order_details,
                    'total': float(total),
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'cashier': request.user.get_full_name() or request.user.username
                }
                messages.success(request, 'Order confirmed successfully..')
                return redirect('orderConfirmation')        
                
            except Exception as e:
                logger.error(f"Error confirming order: {str(e)}")
                messages.error(request, f'Failed to confirm order: {str(e)}')
        
        return render(request, 'customer/index.html', {'recipes': Recipe.objects.filter(is_available=True)})
    
    recipes = Recipe.objects.filter(is_available=True)
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