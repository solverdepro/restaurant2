from django.shortcuts import render, redirect
from .models import Recipe, Product,RecipeIngredient
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.contrib import messages
import logging


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
    if request.method == 'POST':
        logger.debug(f"POST data: {request.POST}")
        action = request.POST.get('action')
        
        if action == 'confirm_order':
            order_items = request.POST.getlist('order_items[]')  # Format: recipe_id:quantity
            try:
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
                
                messages.success(request, 'Order confirmed successfully. Inventory updated.')
            except Exception as e:
                logger.error(f"Error confirming order: {str(e)}")
                messages.error(request, f'Failed to confirm order: {str(e)}')
        
        return render(request, 'customer/index.html', {'recipes': Recipe.objects.filter(is_available=True)})
    
    recipes = Recipe.objects.filter(is_available=True)
    return render(request, 'customer/index.html', {'recipes': recipes})
