from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Product, Supplier, StorageLocation
import uuid

def generate_batch_number():
    return f"BN-{uuid.uuid4().hex[:8].upper()}"

def register_product(request):
    if request.method == 'POST':
        try:
            # Extract form data
            name = request.POST.get('name')
            batch_number = request.POST.get('batchNumber')
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

            # Validate required fields
            if not all([name, batch_number, category, manufacturing_date, expiration_date, quantity, unit]):
                messages.error(request, "Please fill in all required fields.")
                return render(request, 'inventory/add_product.html')

            # Create or get Supplier
            supplier = None
            if supplier_name:
                supplier, _ = Supplier.objects.get_or_create(
                    name=supplier_name,
                    defaults={'contact_number': supplier_contact}
                )

            # Create or get StorageLocation
            storage_location = None
            if storage_area:
                storage_location, _ = StorageLocation.objects.get_or_create(
                    area=storage_area,
                    defaults={'shelf_number': shelf_number or '', 'section': section or ''}
                )

            # Create Product
            product = Product(
                name=name,
                batch_number=batch_number,
                category=category,
                manufacturing_date=manufacturing_date,
                expiration_date=expiration_date,
                quantity=quantity,
                unit=unit,
                supplier=supplier,
                storage_location=storage_location,
                minimum_stock_level=minimum_stock_level if minimum_stock_level else None,
                price=price,
                notes=notes
            )
            product.save()

            messages.success(request, "Product registered successfully!")
            return redirect('registerProduct')

        except Exception as e:
            messages.error(request, f"Error registering product: {str(e)}")
            return render(request, 'inventory/add_product.html')

    # Generate default batch number for GET request
    context = {
        'default_batch_number': generate_batch_number()
    }
    return render(request, 'inventory/add_product.html', context)