from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Product, ProductBatch, Supplier, StorageLocation
import uuid
from django.utils import timezone

def generate_batch_number():
    return f"BN-{uuid.uuid4().hex[:8].upper()}"

def register_product(request):
    if request.method == 'POST':
        try:
            # Extract form data
            name = request.POST.get('name')
            batch_number = request.POST.get('batchNumber') or generate_batch_number()
            category = request.POST.get('category')
            manufacturing_date = request.POST.get('manufacturing_date')
            expiration_date = request.POST.get('expiration_date')
            quantity = request.POST.get('quantity')
            unit = request.POST.get('unit')
            supplier_name = request.POST.get('supplier_name')
            supplier_contact = request.POST.get('supplier_contact')
            storage_area = request.POST.get('storage_area')
            shelf_number = request.POST.get('shelf_number')
            section = request.POST.get('section')
            minimum_stock_level = request.POST.get('minimum_stock_level')
            price = request.POST.get('price')
            notes = request.POST.get('notes', '')

            if not all([name, category, manufacturing_date, expiration_date, quantity, unit]):
                messages.error(request, "Please fill in all required fields.")
                return render(request, 'inventory/add_product.html')

            # ✅ Create or get Supplier
            supplier = None
            if supplier_name:
                supplier, _ = Supplier.objects.get_or_create(
                    name=supplier_name,
                    defaults={'contact_number': supplier_contact}
                )

            # ✅ Create or get StorageLocation
            storage_location = None
            if storage_area:
                storage_location, _ = StorageLocation.objects.get_or_create(
                    area=storage_area,
                    defaults={'shelf_number': shelf_number or '', 'section': section or ''}
                )

            # ✅ Create or get Product (definition only)
            product, _ = Product.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'unit': unit,
                    'minimum_stock_level': minimum_stock_level if minimum_stock_level else None
                }
            )

            # ✅ Create ProductBatch
            ProductBatch.objects.create(
                product=product,
                batch_number=batch_number,
                manufacturing_date=manufacturing_date,
                expiration_date=expiration_date,
                quantity=quantity,
                supplier=supplier,
                storage_location=storage_location,
                price=price,
                notes=notes
            )

            messages.success(request, "Product batch registered successfully!")
            return redirect('registerProduct')

        except Exception as e:
            messages.error(request, f"Error registering product: {str(e)}")
            return render(request, 'inventory/add_product.html')

    context = {'default_batch_number': generate_batch_number()}
    return render(request, 'inventory/add_product.html', context)
