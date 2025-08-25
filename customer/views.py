from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Recipe, Ingredient
from django.core.files.storage import FileSystemStorage
import json

# Create your views here.
def home(request):
    return render(request,'customer/index.html')

def admin_dashboard(request):
    return render(request,'customer/admin_dashboard.html')

def register_recipe(request):
    if request.method == 'POST':
        try:
            # Extract form data
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            category = request.POST.get('category')
            price = request.POST.get('price')
            ingredients_data = json.loads(request.POST.get('ingredients', '[]'))
            image = request.FILES.get('image')

            # Validate required fields
            if not all([name, category, price]):
                messages.error(request, "Please fill in all required fields.")
                return render(request, 'customer/admin_dashboard.html')

            # Create and save Recipe
            recipe = Recipe(
                name=name,
                description=description,
                category=category,
                price=price
            )
            if image:
                recipe.image = image
            recipe.save()

            # Save Ingredients
            for ingredient_data in ingredients_data:
                if ingredient_data.get('name') and ingredient_data.get('amount') and ingredient_data.get('unit'):
                    Ingredient.objects.create(
                        recipe=recipe,
                        name=ingredient_data['name'],
                        amount=ingredient_data['amount'],
                        unit=ingredient_data['unit']
                    )

            messages.success(request, "Recipe registered successfully!")
            return redirect('addrecipe')

        except Exception as e:
            messages.error(request, f"Error registering recipe: {str(e)}")
            return render(request, 'customer/admin_dashboard.html')

    return render(request, 'customer/add_recipe.html')