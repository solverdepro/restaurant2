from django.shortcuts import render, redirect
from .models import Recipe, Product
from django.core.exceptions import ValidationError
from decimal import Decimal

def home(request):
    return render(request,'customer/index.html')

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
        
        # Add ingredients
        if ingredient_ids:
            recipe.ingredients.set(ingredient_ids)
        
        return redirect('homeview')  # Replace with your success URL, e.g., recipe list
        
    return render(request, 'customer/add_recipe.html', {'products': products})