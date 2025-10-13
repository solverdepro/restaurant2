from django.db import models
from inventory.models import Product  
from django.contrib.auth.models import User
from django.utils import timezone

class RecipeIngredient(models.Model):
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE, related_name='recipe_ingredients')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, choices=Product.UNIT_CHOICES)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} {self.unit} for {self.recipe.name}"


    class Meta:
        unique_together = ['recipe', 'product']

class Recipe(models.Model):
    CATEGORY_CHOICES = [
        ('Main Course', 'Main Course'),
        ('Beverage', 'Beverage'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='recipes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    

class Order(models.Model):
    order_id = models.CharField(max_length=50, unique=True)
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    date_time = models.DateTimeField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    items = models.JSONField()  # [{"recipe_id": int, "name": str, "quantity": int, "item_total": float}]

    def __str__(self):
        return self.order_id

    class Meta:
        verbose_name_plural = "Orders"
    