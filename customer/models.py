from django.db import models
from inventory.models import Product  

class RecipeIngredient(models.Model):
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE, related_name='recipe_ingredients')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, choices=Product.UNIT_CHOICES)

    def __str__(self):
        return f"{self.product} - {self.quantity} {self.unit} for {self.recipe}"

    class Meta:
        unique_together = ['recipe', 'product']

class Recipe(models.Model):
    CATEGORY_CHOICES = [
        ('Main Course', 'Main Course'),
        ('Beverage', 'Beverage'),
        # Add more categories as needed
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    ingredients = models.ManyToManyField(Product, related_name='recipes')
    image = models.ImageField(upload_to='recipes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    