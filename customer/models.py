from django.db import models

class Ingredient(models.Model):
    UNIT_CHOICES = [
        ('kg', 'Kilograms'),
        ('g', 'Grams'),
        ('L', 'Liters'),
        ('ml', 'Milliliters'),
        ('pieces', 'Pieces'),
        ('cups', 'Cups'),
        ('tbsp', 'Tablespoons'),
        ('tsp', 'Teaspoons'),
    ]

    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    recipe = models.ForeignKey('Recipe', related_name='ingredients', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.amount} {self.unit})"

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

    def __str__(self):
        return self.name