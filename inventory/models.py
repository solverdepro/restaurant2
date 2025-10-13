from django.db import models

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_number = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.name

class StorageLocation(models.Model):
    area = models.CharField(max_length=100, choices=[
        ('Dry Storage', 'Dry Storage'),
        ('Refrigerator', 'Refrigerator'),
        ('Freezer', 'Freezer'),
        ('Pantry', 'Pantry'),
    ])
    shelf_number = models.CharField(max_length=50, blank=True)
    section = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.area} - {self.shelf_number} - {self.section}"

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Dairy', 'Dairy'),
        ('Meat', 'Meat'),
        ('Vegetables', 'Vegetables'),
        ('Fruits', 'Fruits'),
        ('Grains', 'Grains'),
        ('Spices', 'Spices'),
        ('Beverages', 'Beverages'),
        ('Cleaning Supplies', 'Cleaning Supplies'),
        ('Packaging', 'Packaging'),
    ]

    UNIT_CHOICES = [
        ('kg', 'Kilograms'),
        ('g', 'Grams'),
        ('L', 'Liters'),
        ('ml', 'Milliliters'),
        ('pieces', 'Pieces'),
        ('boxes', 'Boxes'),
        ('packets', 'Packets'),
        ('bags', 'Bags'),
        ('bottles', 'Bottles'),
        ('jars', 'Jars'),
    ]

    # name = models.CharField(max_length=200, unique=True)
    # category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    # unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    # minimum_stock_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # def __str__(self):
    #     return self.name
    name = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    minimum_stock_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    storage_location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, null=True, blank=True)
    additional_info = models.TextField(blank=True)

    def __str__(self):
        return self.name

# class ProductBatch(models.Model):
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="batches")
#     batch_number = models.CharField(max_length=50)
#     manufacturing_date = models.DateField()
#     expiration_date = models.DateField()
#     quantity = models.DecimalField(max_digits=10, decimal_places=2)
#     supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
#     storage_location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, null=True, blank=True)
#     price = models.DecimalField(max_digits=10, decimal_places=2)
#     notes = models.TextField(blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ["expiration_date"] 

#     def __str__(self):
#         return f"{self.product.name} - Batch {self.batch_number} (exp: {self.expiration_date})"

class ProductBatch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="batches")
    batch_number = models.CharField(max_length=50)
    manufacturing_date = models.DateField()
    expiration_date = models.DateField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price per quantity added
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expiration_date"]  # FEFO ready!

    def __str__(self):
        return f"{self.product.name} - Batch {self.batch_number} (exp: {self.expiration_date})"