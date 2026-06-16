from django.shortcuts import render, redirect,get_object_or_404,HttpResponse
from django.contrib import messages
from .models import Product, ProductBatch, Supplier, StorageLocation, InventoryTransaction
import uuid
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
import logging
from django.db import models
from django.db.models import Q
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from django.db.models import Sum, Count,F
from datetime import datetime, timedelta
from user_auth.models import Staff




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


            batch = ProductBatch.objects.create(
                product=product,
                batch_number=batch_number,
                manufacturing_date=manufacturing_date,
                expiration_date=expiration_date,
                quantity=quantity,
                price=price,
                notes=notes
            )

            # Auto-record a Stock In transaction for this batch
            staff = None
            if request.user.is_authenticated and hasattr(request.user, 'staff_profile'):
                staff = request.user.staff_profile

            InventoryTransaction.objects.create(
                batch=batch,
                transaction_type='Stock In',
                quantity=batch.quantity,
                unit_price=batch.price,
                staff=staff,
                notes=notes or f"Initial stock in for batch {batch.batch_number}"
            )

            messages.success(request, "Product batch added successfully!")
            return redirect('productView')

        except Exception as e:
            messages.error(request, f"Error adding product batch: {str(e)}")
            return render(request, 'inventory/add_batch.html', {'products': products})

    return render(request, 'inventory/add_batch.html', {'products': products})


def product_view(request):
    products = Product.objects.select_related('supplier', 'storage_location')

    # Optional: annotate products with batch info if needed
    product_batches = {}
    today = timezone.now().date()

    for product in products:
        batches = ProductBatch.objects.filter(product=product)
        batch_info = []
        for b in batches:
            days_left = (b.expiration_date - today).days
            if days_left < 0:
                status = "expired"
            elif days_left <= 14:
                status = "expiring-soon"
            elif b.quantity <= (product.minimum_stock_level or 0):
                status = "low-stock"
            else:
                status = "in-stock"
            batch_info.append({
                'batch_number': b.batch_number,
                'quantity': b.quantity,
                'price': b.price,
                'expiration_date': b.expiration_date,
                'status': status,
                'days_left': days_left
            })
        product_batches[product.id] = batch_info

    return render(request, 'inventory/product_view.html', {
        'products': products,
        'product_batches': product_batches
    })
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()  # cascades to batches if you set on_delete=models.CASCADE in ProductBatch
    messages.success(request, "Product deleted successfully.")
    return redirect('productView')



def update_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    batches = ProductBatch.objects.filter(product=product)

    if request.method == 'POST':
        try:
            # Product fields
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
                return render(request, 'inventory/update_product.html', {'product': product, 'batches': batches})

            # Supplier
            supplier = None
            if supplier_name:
                supplier, _ = Supplier.objects.get_or_create(
                    name=supplier_name,
                    defaults={'contact_number': supplier_contact}
                )

            # Storage location
            storage_location = None
            if storage_area:
                storage_location, _ = StorageLocation.objects.get_or_create(
                    area=storage_area,
                    defaults={'shelf_number': shelf_number or '', 'section': section or ''}
                )

            # Update Product
            product.name = name
            product.category = category
            product.unit = unit
            product.minimum_stock_level = minimum_stock_level if minimum_stock_level else None
            product.supplier = supplier
            product.storage_location = storage_location
            product.additional_info = additional_info
            product.save()

            messages.success(request, "Product updated successfully!")
            return redirect('productView')

        except Exception as e:
            logger.error(f"Error updating product: {str(e)}")
            messages.error(request, f"Error updating product: {str(e)}")
            return render(request, 'inventory/update_product.html', {'product': product, 'batches': batches})

    return render(request, 'inventory/update_product.html', {'product': product, 'batches': batches})

def search_products(request):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    today = timezone.now().date()

    products = Product.objects.select_related('supplier', 'storage_location')

    # Apply search filters
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(supplier__name__icontains=search_query)
        )

    data = []

    for product in products:
        batches = ProductBatch.objects.filter(product=product)
        if batches.exists():
            for batch in batches:
                days_left = (batch.expiration_date - today).days
                batch_status = (
                    'expired' if days_left < 0 else
                    'expiring-soon' if days_left <= 14 else
                    'low-stock' if batch.quantity <= (product.minimum_stock_level or 0) else
                    'in-stock'
                )
                # Apply status filter
                if status_filter and batch_status != status_filter:
                    continue

                data.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'batch_number': batch.batch_number,
                    'quantity': f"{batch.quantity} {product.unit}",
                    'price': float(batch.price),
                    'created_at': batch.created_at.strftime('%Y-%m-%d'),
                    'updated_at': batch.updated_at.strftime('%Y-%m-%d'),
                    'expiration_date': batch.expiration_date.strftime('%Y-%m-%d'),
                    'days_left': days_left,
                    'status': batch_status,
                    'supplier': {
                        'name': product.supplier.name if product.supplier else '—',
                        'contact_number': product.supplier.contact_number if product.supplier else ''
                    },
                    'edit_url': reverse('update_product', args=[product.id]),
                    'delete_url': reverse('delete_product', args=[product.id]),
                })
        else:
            # Include product with no batches
            if not status_filter or status_filter in ['in-stock', 'no-batch']:
                data.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'batch_number': '—',
                    'quantity': '—',
                    'price': '—',
                    'created_at': '—',
                    'updated_at': '—',
                    'expiration_date': '—',
                    'days_left': '—',
                    'status': 'no-batch',
                    'supplier': {
                        'name': product.supplier.name if product.supplier else '—',
                        'contact_number': product.supplier.contact_number if product.supplier else ''
                    },
                    'edit_url': reverse('update_product', args=[product.id]),
                    'delete_url': reverse('delete_product', args=[product.id]),
                })

    return JsonResponse({'batches': data})

def inventory_report(request):
    staffs = Staff.objects.filter(role='Cashier')
    transactions = InventoryTransaction.objects.select_related('batch__product', 'staff__user')
    products = Product.objects.all().order_by('name')

    if request.method == 'POST' and request.POST.get('action') == 'export_pdf':
        try:
            date_range = request.POST.get('date_range', 'this_week')
            from_date = request.POST.get('from_date')
            to_date = request.POST.get('to_date')
            transaction_type = request.POST.get('transaction_type', 'All Transactions')
            product_id = request.POST.get('product', 'all')

            # Filter transactions
            filtered_transactions = InventoryTransaction.objects.select_related('batch__product', 'staff__user')
            if transaction_type != 'All Transactions':
                filtered_transactions = filtered_transactions.filter(transaction_type=transaction_type)
            if product_id and product_id != 'all':
                filtered_transactions = filtered_transactions.filter(batch__product_id=product_id)

            if date_range == 'today':
                filtered_transactions = filtered_transactions.filter(timestamp__date=timezone.now().date())
            elif date_range == 'this_week':
                start_of_week = timezone.now().date() - timedelta(days=timezone.now().weekday())
                filtered_transactions = filtered_transactions.filter(timestamp__date__gte=start_of_week)
            elif date_range == 'this_month':
                start_of_month = timezone.now().date().replace(day=1)
                filtered_transactions = filtered_transactions.filter(timestamp__date__gte=start_of_month)
            elif date_range == 'last_month':
                last_month = timezone.now().date().replace(day=1) - timedelta(days=1)
                start_of_last_month = last_month.replace(day=1)
                filtered_transactions = filtered_transactions.filter(
                    timestamp__date__gte=start_of_last_month,
                    timestamp__date__lte=last_month
                )
            elif date_range == 'custom' and from_date and to_date:
                filtered_transactions = filtered_transactions.filter(
                    timestamp__date__gte=from_date,
                    timestamp__date__lte=to_date
                )

            # Generate PDF
            buffer = BytesIO()
            
            # Setup document margins to 36 (0.5 inch)
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                leftMargin=36,
                rightMargin=36,
                topMargin=36,
                bottomMargin=36
            )
            
            styles = getSampleStyleSheet()
            elements = []

            # Custom ParagraphStyles
            from reportlab.lib.styles import ParagraphStyle
            
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Title'],
                textColor=colors.HexColor('#e8731e'),
                fontSize=22,
                fontName='Helvetica-Bold',
                spaceAfter=15,
                alignment=0 # Left-aligned
            )
            
            meta_label_style = ParagraphStyle(
                'MetaLabel',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#475569'), # Slate-600
                fontName='Helvetica',
                spaceAfter=3
            )
            
            cell_header_style = ParagraphStyle(
                'CellHeader',
                parent=styles['Normal'],
                textColor=colors.white,
                fontSize=9,
                fontName='Helvetica-Bold',
                alignment=1 # Center
            )
            
            cell_body_left = ParagraphStyle(
                'CellBodyLeft',
                parent=styles['Normal'],
                fontSize=8.5,
                textColor=colors.HexColor('#1e293b'), # Slate-800
                fontName='Helvetica',
                alignment=0 # Left
            )
            
            cell_body_center = ParagraphStyle(
                'CellBodyCenter',
                parent=styles['Normal'],
                fontSize=8.5,
                textColor=colors.HexColor('#1e293b'), # Slate-800
                fontName='Helvetica',
                alignment=1 # Center
            )

            # Title
            elements.append(Paragraph("Inventory Transaction Report", title_style))

            # Metadata Info Block
            date_text = f"Date Range: {date_range.replace('_', ' ').title()}"
            if date_range == 'custom':
                date_text = f"Date Range: {from_date} to {to_date}"
            
            elements.append(Paragraph(f"<b>{date_text}</b>", meta_label_style))
            elements.append(Paragraph(f"<b>Transaction Type:</b> {transaction_type}", meta_label_style))
            if product_id and product_id != 'all':
                try:
                    selected_prod = Product.objects.get(id=product_id)
                    elements.append(Paragraph(f"<b>Filtered Product:</b> {selected_prod.name} ({selected_prod.unit})", meta_label_style))
                except Product.DoesNotExist:
                    pass
            
            elements.append(Paragraph("<br/>", styles['Normal']))

            # Calculate Summary values
            expr = F('quantity') * F('unit_price')
            stock_in_val = filtered_transactions.filter(transaction_type='Stock In').aggregate(total=Sum(expr))['total'] or 0
            stock_out_val = filtered_transactions.filter(transaction_type='Stock Out').aggregate(total=Sum(expr))['total'] or 0
            adj_val = filtered_transactions.filter(transaction_type='Adjustment').aggregate(total=Sum(expr))['total'] or 0

            # Organize summary items into a beautiful 3-column grid structure
            sum_header_style = ParagraphStyle('SumHeader', parent=styles['Normal'], fontSize=8.5, textColor=colors.HexColor('#64748b'), fontName='Helvetica-Bold', spaceAfter=3)
            sum_value_style = ParagraphStyle('SumValue', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#1e293b'), fontName='Helvetica-Bold')
            sum_qty_style = ParagraphStyle('SumQty', parent=styles['Normal'], fontSize=8.5, textColor=colors.HexColor('#475569'), fontName='Helvetica')

            summary_table_data = [
                [
                    Paragraph("STOCK IN", sum_header_style),
                    Paragraph("STOCK OUT", sum_header_style),
                    Paragraph("ADJUSTMENTS", sum_header_style)
                ],
                [
                    Paragraph(f"Tsh {stock_in_val:,.2f}", sum_value_style),
                    Paragraph(f"Tsh {stock_out_val:,.2f}", sum_value_style),
                    Paragraph(f"Tsh {adj_val:,.2f}", sum_value_style)
                ]
            ]

            if product_id and product_id != 'all':
                try:
                    selected_prod = Product.objects.get(id=product_id)
                    stock_in_qty = filtered_transactions.filter(transaction_type='Stock In').aggregate(total=Sum('quantity'))['total'] or 0
                    stock_out_qty = filtered_transactions.filter(transaction_type='Stock Out').aggregate(total=Sum('quantity'))['total'] or 0
                    adj_qty = filtered_transactions.filter(transaction_type='Adjustment').aggregate(total=Sum('quantity'))['total'] or 0
                    
                    summary_table_data.append([
                        Paragraph(f"Total Qty: {stock_in_qty:,.2f} {selected_prod.unit}", sum_qty_style),
                        Paragraph(f"Total Qty: {stock_out_qty:,.2f} {selected_prod.unit}", sum_qty_style),
                        Paragraph(f"Total Qty: {adj_qty:,.2f} {selected_prod.unit}", sum_qty_style)
                    ])
                except Product.DoesNotExist:
                    pass

            # Inner table width is 499 (523 total outer width - 24 points padding)
            summary_table = Table(summary_table_data, colWidths=[166, 166, 167])
            summary_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))

            # Create report summary card box
            summary_elements = [
                Paragraph("<b>REPORT SUMMARY</b>", ParagraphStyle('Sub', parent=styles['Normal'], textColor=colors.HexColor('#e8731e'), fontSize=9.5, fontName='Helvetica-Bold', spaceAfter=8)),
                summary_table
            ]

            summary_box = Table([[summary_elements]], colWidths=[523])
            summary_box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ]))
            
            elements.append(summary_box)
            elements.append(Paragraph("<br/>", styles['Normal']))

            # Table Data with wrapped headers/body
            data = [[
                Paragraph('Date & Time', cell_header_style),
                Paragraph('Product', cell_header_style),
                Paragraph('Batch No', cell_header_style),
                Paragraph('Type', cell_header_style),
                Paragraph('Quantity', cell_header_style),
                Paragraph('Unit Price', cell_header_style),
                Paragraph('Total Value', cell_header_style),
                Paragraph('Staff', cell_header_style),
            ]]
            
            for t in filtered_transactions:
                staff_name = f"{t.staff.user.first_name} {t.staff.user.last_name}" if t.staff else '—'
                data.append([
                    Paragraph(t.timestamp.strftime('%Y-%m-%d %H:%M'), cell_body_center),
                    Paragraph(t.batch.product.name, cell_body_left),
                    Paragraph(t.batch.batch_number, cell_body_center),
                    Paragraph(t.transaction_type, cell_body_center),
                    Paragraph(f"{t.quantity} {t.batch.product.unit}", cell_body_center),
                    Paragraph(f"Tsh {t.unit_price:,.2f}", cell_body_center),
                    Paragraph(f"Tsh {t.total_value():,.2f}", cell_body_center),
                    Paragraph(staff_name, cell_body_left)
                ])

            # colWidths must sum to exactly 523
            table = Table(data, colWidths=[90, 93, 55, 60, 55, 55, 60, 55])
            
            table_style_list = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8731e')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]
            
            # Alternating white/slate background
            for i in range(1, len(data)):
                if i % 2 == 0:
                    table_style_list.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8fafc')))
                else:
                    table_style_list.append(('BACKGROUND', (0, i), (-1, i), colors.white))
            
            table.setStyle(TableStyle(table_style_list))
            elements.append(table)

            # Build document with header and footer decoration callback
            def add_header_footer(canvas_obj, doc_obj):
                canvas_obj.saveState()
                # Footer
                canvas_obj.setFont('Helvetica', 8)
                canvas_obj.setFillColor(colors.HexColor('#64748b'))
                canvas_obj.drawString(36, 20, f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
                canvas_obj.drawRightString(595.27 - 36, 20, f"Page {doc_obj.page}")
                
                # Header Brand Accent Line
                canvas_obj.setStrokeColor(colors.HexColor('#e8731e'))
                canvas_obj.setLineWidth(2.5)
                canvas_obj.line(36, 841.89 - 25, 595.27 - 36, 841.89 - 25)
                canvas_obj.restoreState()

            doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
            buffer.seek(0)
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="inventory_report.pdf"'
            response.write(buffer.read())
            buffer.close()
            return response

        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            messages.error(request, f"Error generating PDF: {str(e)}")

    return render(request, 'inventory/inventory_report.html', {'staffs': staffs, 'transactions': transactions, 'products': products})

def search_inventory_report(request):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    date_range = request.GET.get('date_range', 'all')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    transaction_type = request.GET.get('transaction_type', 'All Transactions')
    product_id = request.GET.get('product', 'all')

    transactions = InventoryTransaction.objects.select_related('batch__product', 'staff__user')

    # Apply filters
    if transaction_type != 'All Transactions':
        transactions = transactions.filter(transaction_type=transaction_type)

    if product_id and product_id != 'all':
        transactions = transactions.filter(batch__product_id=product_id)

    if date_range == 'today':
        transactions = transactions.filter(timestamp__date=timezone.now().date())
    elif date_range == 'this_week':
        start_of_week = timezone.now().date() - timedelta(days=timezone.now().weekday())
        transactions = transactions.filter(timestamp__date__gte=start_of_week)
    elif date_range == 'this_month':
        start_of_month = timezone.now().date().replace(day=1)
        transactions = transactions.filter(timestamp__date__gte=start_of_month)
    elif date_range == 'last_month':
        last_month = timezone.now().date().replace(day=1) - timedelta(days=1)
        start_of_last_month = last_month.replace(day=1)
        transactions = transactions.filter(
            timestamp__date__gte=start_of_last_month,
            timestamp__date__lte=last_month
        )
    elif date_range == 'custom' and from_date and to_date:
        transactions = transactions.filter(
            timestamp__date__gte=from_date,
            timestamp__date__lte=to_date
        )

    # Product unit
    product_unit = ''
    if product_id and product_id != 'all':
        try:
            product_unit = Product.objects.get(id=product_id).unit
        except Product.DoesNotExist:
            pass

    # Summary data
    expr = F('quantity') * F('unit_price')
    stock_in = transactions.filter(transaction_type='Stock In').aggregate(
        total_items=Count('id'),
        total_value=Sum(expr),
        total_qty=Sum('quantity')
    )
    stock_out = transactions.filter(transaction_type='Stock Out').aggregate(
        total_items=Count('id'),
        total_value=Sum(expr),
        total_qty=Sum('quantity')
    )
    adjustments = transactions.filter(transaction_type='Adjustment').aggregate(
        total_items=Count('id'),
        total_value=Sum(expr),
        total_qty=Sum('quantity')
    )
    most_active = (transactions
                   .values('batch__product__name')
                   .annotate(transaction_count=Count('id'))
                   .order_by('-transaction_count')
                   .first())

    # Chart data
    days = [(timezone.now().date() - timedelta(days=x)) for x in range(6, -1, -1)]
    labels = [d.strftime('%a') for d in days]
    stock_in_data = [
        transactions.filter(transaction_type='Stock In', timestamp__date=d).count()
        for d in days
    ]
    stock_out_data = [
        transactions.filter(transaction_type='Stock Out', timestamp__date=d).count()
        for d in days
    ]

    # Prepare response
    data = {
        'product_unit': product_unit,
        'transactions': [{
            'timestamp': t.timestamp.strftime('%Y-%m-%d %H:%M'),
            'product': t.batch.product.name,
            'batch_number': t.batch.batch_number,
            'transaction_type': t.transaction_type,
            'quantity': f"{t.quantity} {t.batch.product.unit}",
            'unit_price': float(t.unit_price),
            'total_value': float(t.total_value()),
            'staff': f"{t.staff.user.first_name} {t.staff.user.last_name}" if t.staff else '—'
        } for t in transactions],
        'summary': {
            'stock_in': {
                'items': stock_in['total_items'] or 0,
                'value': float(stock_in['total_value'] or 0),
                'quantity': float(stock_in['total_qty'] or 0)
            },
            'stock_out': {
                'items': stock_out['total_items'] or 0,
                'value': float(stock_out['total_value'] or 0),
                'quantity': float(stock_out['total_qty'] or 0)
            },
            'adjustments': {
                'items': adjustments['total_items'] or 0,
                'value': float(adjustments['total_value'] or 0),
                'quantity': float(adjustments['total_qty'] or 0)
            },
            'most_active': {
                'product': most_active['batch__product__name'] if most_active else '—',
                'transactions': most_active['transaction_count'] if most_active else 0
            }
        },
        'chart_data': {
            'labels': labels,
            'stock_in': stock_in_data,
            'stock_out': stock_out_data
        }
    }

    return JsonResponse(data)

