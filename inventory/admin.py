from django.contrib import admin
from .models import Supplier,StorageLocation,Product


# Register your models here.
admin.site.register(Supplier)
admin.site.register(StorageLocation)
admin.site.register(Product)