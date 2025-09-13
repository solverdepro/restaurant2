from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Product, ProductBatch, Supplier, StorageLocation
import uuid
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
import logging
from django.db import models


logger = logging.getLogger(__name__)


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

def product_view(request):
    batches = ProductBatch.objects.select_related("product", "supplier", "storage_location")
    today = timezone.now().date()

    for b in batches:
        days_left = (b.expiration_date - today).days
        if days_left < 0:
            b.status = "expired"
        elif days_left <= 14:
            b.status = "expiring-soon"
        elif b.quantity <= (b.product.minimum_stock_level or 0):
            b.status = "low-stock"
        else:
            b.status = "in-stock"
        b.days_left = days_left
    return render(request,'inventory/product_view.html',{'batches': batches})

def update_product(request, batch_id):
    # logic to update product batch
    pass

def delete_product(request, batch_id):
    batch = ProductBatch.objects.get(id=batch_id)
    batch.delete()
    messages.success(request, "Product batch deleted successfully!")
    return redirect('productView')

def update_product(request, batch_id):
    batch = ProductBatch.objects.get(id=batch_id)
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

            if not all([name, category, manufacturing_date, expiration_date, quantity, unit, batch_number, price]):
                messages.error(request, "Please fill in all required fields.")
                return render(request, 'inventory/update_product.html', {
                    'batch': batch,
                    'products': Product.objects.all(),
                    'suppliers': Supplier.objects.all(),
                    'storage_locations': StorageLocation.objects.all()
                })

            # Update or create Supplier
            supplier = None
            if supplier_name:
                supplier, _ = Supplier.objects.get_or_create(
                    name=supplier_name,
                    defaults={'contact_number': supplier_contact}
                )

            # Update or create StorageLocation
            storage_location = None
            if storage_area:
                storage_location, _ = StorageLocation.objects.get_or_create(
                    area=storage_area,
                    defaults={'shelf_number': shelf_number or '', 'section': section or ''}
                )

            # Update or create Product
            product, _ = Product.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'unit': unit,
                    'minimum_stock_level': minimum_stock_level if minimum_stock_level else None
                }
            )

            # Update ProductBatch
            batch.product = product
            batch.batch_number = batch_number
            batch.manufacturing_date = manufacturing_date
            batch.expiration_date = expiration_date
            batch.quantity = quantity
            batch.supplier = supplier
            batch.storage_location = storage_location
            batch.price = price
            batch.notes = notes
            batch.save()

            messages.success(request, "Product batch updated successfully!")
            return redirect('productView')

        except Exception as e:
            logger.error(f"Error updating product batch: {str(e)}")
            messages.error(request, f"Error updating product: {str(e)}")
            return render(request, 'inventory/update_product.html', {
                'batch': batch,
                'products': Product.objects.all(),
                'suppliers': Supplier.objects.all(),
                'storage_locations': StorageLocation.objects.all()
            })

    return render(request, 'inventory/update_product.html', {
        'batch': batch,
        'products': Product.objects.all(),
        'suppliers': Supplier.objects.all(),
        'storage_locations': StorageLocation.objects.all()
    })

def search_products(request):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    search_query = request.GET.get('search', '').strip()
    category = request.GET.get('category', '')
    status = request.GET.get('status', '')

    batches = ProductBatch.objects.select_related('product', 'supplier', 'storage_location')
    today = timezone.now().date()

    # Apply filters
    if search_query:
        batches = batches.filter(
            models.Q(product__name__icontains=search_query) |
            models.Q(batch_number__icontains=search_query) |
            models.Q(supplier__name__icontains=search_query)
        )

    if category:
        batches = batches.filter(product__category=category)

    if status:
        filtered_batches = []
        for batch in batches:
            days_left = (batch.expiration_date - today).days
            batch_status = (
                'expired' if days_left < 0 else
                'expiring-soon' if days_left <= 14 else
                'low-stock' if batch.quantity <= (batch.product.minimum_stock_level or 0) else
                'in-stock'
            )
            if batch_status == status:
                filtered_batches.append(batch.id)
        batches = batches.filter(id__in=filtered_batches)

    # Prepare response data
    data = []
    for batch in batches:
        days_left = (batch.expiration_date - today).days
        data.append({
            'product_name': batch.product.name,
            'batch_number': batch.batch_number,
            'quantity': f"{batch.quantity} {batch.product.unit}",
            'price': float(batch.price),
            'created_at': batch.created_at.strftime('%Y-%m-%d'),
            'updated_at': batch.updated_at.strftime('%Y-%m-%d'),
            'expiration_date': batch.expiration_date.strftime('%Y-%m-%d'),
            'days_left': days_left,
            'supplier': {
                'name': batch.supplier.name if batch.supplier else '—',
                'contact_number': batch.supplier.contact_number if batch.supplier else ''
            },
            'edit_url': reverse('update_product', args=[batch.id]),
            'delete_url': reverse('delete_product', args=[batch.id])
        })

    return JsonResponse({'batches': data})