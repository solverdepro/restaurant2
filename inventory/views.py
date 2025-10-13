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

def add_product(request):
    # Pass choices for dropdowns
    category_choices = Product.CATEGORY_CHOICES
    unit_choices = Product.UNIT_CHOICES
    storage_choices = StorageLocation.objects.all()  # if it's a class method returning list of tuples

    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            category = request.POST.get('category')
            unit = request.POST.get('unit')
            minimum_stock_level = request.POST.get('minimum_stock_level')
            supplier_name = request.POST.get('supplier_name')
            supplier_contact = request.POST.get('supplier_contact')
            storage_area = request.POST.get('storage_area')
            shelf_number = request.POST.get('shelf_number')
            section = request.POST.get('section')
            additional_info = request.POST.get('additional_info', '')

            if not all([name, category, unit]):
                messages.error(request, "Please fill in all required fields.")
                return render(
                    request, 
                    'inventory/add_product.html',
                    {
                        'category_choices': category_choices,
                        'unit_choices': unit_choices,
                        'storage_choices': storage_choices
                    }
                )

            supplier = None
            if supplier_name:
                supplier, _ = Supplier.objects.get_or_create(
                    name=supplier_name,
                    defaults={'contact_number': supplier_contact}
                )

            storage_location = None
            if storage_area:
                storage_location, _ = StorageLocation.objects.get_or_create(
                    area=storage_area,
                    defaults={'shelf_number': shelf_number or '', 'section': section or ''}
                )

            Product.objects.create(
                name=name,
                category=category,
                unit=unit,
                minimum_stock_level=minimum_stock_level if minimum_stock_level else None,
                supplier=supplier,
                storage_location=storage_location,
                additional_info=additional_info
            )

            messages.success(request, "Product added successfully!")
            return redirect('productView')

        except Exception as e:
            messages.error(request, f"Error adding product: {str(e)}")
            return render(
                request, 
                'inventory/add_product.html',
                {
                    'category_choices': category_choices,
                    'unit_choices': unit_choices,
                    'storage_choices': storage_choices
                }
            )

    return render(
        request, 
        'inventory/add_product.html',
        {
            'category_choices': category_choices,
            'unit_choices': unit_choices,
            'storage_choices': storage_choices
        }
    )


def add_batch(request):
    products = Product.objects.all()
    
    if request.method == 'POST':
        try:
            product_id = request.POST.get('product')
            batch_number = request.POST.get('batchNumber') or generate_batch_number()
            manufacturing_date = request.POST.get('manufacturing_date')
            expiration_date = request.POST.get('expiration_date')
            quantity = request.POST.get('quantity')
            price = request.POST.get('price')
            notes = request.POST.get('notes', '')

            if not all([product_id, manufacturing_date, expiration_date, quantity, price]):
                messages.error(request, "Please fill in all required fields.")
                return render(request, 'inventory/add_batch.html', {'products': products})

            product = Product.objects.get(id=product_id)

            # ✅ Check for duplicate batch for the same product
            if ProductBatch.objects.filter(product=product, batch_number=batch_number).exists():
                messages.error(request, f"A batch with number '{batch_number}' already exists for this product.")
                return render(request, 'inventory/add_batch.html', {'products': products})


            ProductBatch.objects.create(
                product=product,
                batch_number=batch_number,
                manufacturing_date=manufacturing_date,
                expiration_date=expiration_date,
                quantity=quantity,
                price=price,
                notes=notes
            )

            messages.success(request, "Product batch added successfully!")
            return redirect('productView')

        except Exception as e:
            messages.error(request, f"Error adding product batch: {str(e)}")
            return render(request, 'inventory/add_batch.html', {'products': products})

    return render(request, 'inventory/add_batch.html', {'products': products})

def product_view(request):
    batches = ProductBatch.objects.select_related("product", "product__supplier", "product__storage_location")
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

def delete_product(request, batch_id):
    batch = ProductBatch.objects.get(id=batch_id)
    batch.delete()
    messages.success(request, "Product batch deleted successfully!")
    return redirect('productView')

def update_product(request, batch_id):
    batch = ProductBatch.objects.get(id=batch_id)
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            category = request.POST.get('category')
            unit = request.POST.get('unit')
            minimum_stock_level = request.POST.get('minimum_stock_level')
            supplier_name = request.POST.get('supplier_name')
            supplier_contact = request.POST.get('supplier_contact')
            storage_area = request.POST.get('storage_area')
            shelf_number = request.POST.get('shelf_number')
            section = request.POST.get('section')
            additional_info = request.POST.get('additional_info', '')
            batch_number = request.POST.get('batchNumber')
            manufacturing_date = request.POST.get('manufacturing_date')
            expiration_date = request.POST.get('expiration_date')
            quantity = request.POST.get('quantity')
            price = request.POST.get('price')
            notes = request.POST.get('notes', '')

            if not all([name, category, unit, batch_number, manufacturing_date, expiration_date, quantity, price]):
                messages.error(request, "Please fill in all required fields.")
                return render(request, 'inventory/update_product.html', {'batch': batch})

            supplier = None
            if supplier_name:
                supplier, _ = Supplier.objects.get_or_create(
                    name=supplier_name,
                    defaults={'contact_number': supplier_contact}
                )

            storage_location = None
            if storage_area:
                storage_location, _ = StorageLocation.objects.get_or_create(
                    area=storage_area,
                    defaults={'shelf_number': shelf_number or '', 'section': section or ''}
                )

            # Update Product (static)
            batch.product.name = name
            batch.product.category = category
            batch.product.unit = unit
            batch.product.minimum_stock_level = minimum_stock_level if minimum_stock_level else None
            batch.product.supplier = supplier
            batch.product.storage_location = storage_location
            batch.product.additional_info = additional_info
            batch.product.save()

            # Update ProductBatch (dynamic)
            batch.batch_number = batch_number
            batch.manufacturing_date = manufacturing_date
            batch.expiration_date = expiration_date
            batch.quantity = quantity
            batch.price = price
            batch.notes = notes
            batch.save()

            messages.success(request, "Product batch updated successfully!")
            return redirect('productView')

        except Exception as e:
            logger.error(f"Error updating product batch: {str(e)}")
            messages.error(request, f"Error updating product: {str(e)}")
            return render(request, 'inventory/update_product.html', {'batch': batch})

    return render(request, 'inventory/update_product.html', {'batch': batch})
def search_products(request):
    # Ensure it's an AJAX request
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    search_query = request.GET.get('search', '').strip()
    status = request.GET.get('status', '').strip()

    batches = ProductBatch.objects.select_related(
        'product', 'product__supplier', 'product__storage_location'
    )
    today = timezone.now().date()

    # ✅ Apply search filters (fixed supplier reference)
    if search_query:
        batches = batches.filter(
            models.Q(product__name__icontains=search_query) |
            models.Q(batch_number__icontains=search_query) |
            models.Q(product__supplier__name__icontains=search_query)
        )

    # ✅ Apply status filter
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

    # ✅ Prepare response data
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
                'name': batch.product.supplier.name if batch.product.supplier else '—',
                'contact_number': batch.product.supplier.contact_number if batch.product.supplier else ''
            },
            'edit_url': reverse('update_product', args=[batch.id]),
            'delete_url': reverse('delete_product', args=[batch.id]),
        })

    return JsonResponse({'batches': data})