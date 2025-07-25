from flask import render_template, redirect, url_for, flash, request, jsonify, make_response, send_file, abort
from flask_login import login_required, current_user
from app.models import Device, Sale
from app.forms import SaleForm
from app.routes.sales import bp
from app.utils.decorators import staff_required
from app import db
from decimal import Decimal
from datetime import datetime
import pdfkit
from weasyprint import HTML
from io import BytesIO
from collections import defaultdict

@bp.route('/')
@login_required
def index():
    """Display sales dashboard"""
    if current_user.is_admin():
        sales = Sale.query.order_by(Sale.sale_date.desc()).all()
    else:
        sales = Sale.query.filter_by(seller_id=current_user.id).order_by(Sale.sale_date.desc()).all()
    return render_template('sales/index.html', sales=sales)

@bp.route('/new', methods=['GET', 'POST'])
@login_required
@staff_required
def new_sale():
    """Show new sale form and handle form submission"""
    form = SaleForm()
    if form.validate_on_submit():
        device = Device.query.filter_by(imei=form.imei.data, status='available').first()
        if not device:
            flash('Device not found or not available', 'danger')
            return render_template('sales/new.html', form=form)

        try:
            # Create sale record
            sale = Sale(
                device=device,
                seller=current_user,
                sale_price=form.sale_price.data,
                payment_type=form.payment_type.data,
                amount_paid=form.amount_paid.data,
                notes=form.notes.data
            )
            
            # Mark device as sold
            device.mark_as_sold()
            
            # Save changes
            db.session.add(sale)
            db.session.commit()
            
            flash('Sale recorded successfully!', 'success')
            return redirect(url_for('sales.detail', sale_id=sale.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error recording sale: {str(e)}', 'danger')
            
    return render_template('sales/new.html', form=form)

@bp.route('/create', methods=['POST'])
@login_required
@staff_required
def create_sale():
    """Create a new sale"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['imei', 'sale_price', 'payment_type', 'amount_paid']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Get device and validate availability
    device = Device.query.filter_by(imei=data['imei'], status='available').first()
    if not device:
        return jsonify({'error': 'Device not found or not available'}), 404
    
    try:
        # Create sale record
        sale = Sale(
            device=device,
            seller=current_user,
            sale_price=Decimal(data['sale_price']),
            payment_type=data['payment_type'],
            amount_paid=Decimal(data['amount_paid']),
            notes=data.get('notes', '')
        )
        
        # Mark device as sold
        device.mark_as_sold()
        
        # Save changes
        db.session.add(sale)
        db.session.commit()
        
        flash('Sale recorded successfully!', 'success')
        return jsonify(sale.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/sales/check_imei/<imei>')
@login_required
def check_imei(imei):
    device = Device.query.filter_by(imei=imei, status='available').first()
    if device:
        return jsonify({
            'found': True,
            'brand': device.brand,
            'model': device.model,
            'purchase_price': device.purchase_price
        })
    return jsonify({'found': False})

@bp.route('/device/<imei>', methods=['GET'])
@login_required
@staff_required
def get_device(imei):
    """Get device details by IMEI for sale"""
    device = Device.query.filter_by(imei=imei, status='available').first()
    if not device:
        return jsonify({'error': 'Device not found or not available'}), 404
    return jsonify(device.to_dict())

@bp.route('/detail/<int:sale_id>')
@login_required
def sale_detail(sale_id):
    """Show sale details"""
    sale = Sale.query.get_or_404(sale_id)
    if not current_user.is_admin() and sale.seller_id != current_user.id:
        flash('You do not have permission to view this sale.', 'error')
        return redirect(url_for('sales.index'))
    return render_template('sales/detail.html', sale=sale)

@bp.route('/update_payment/<int:sale_id>', methods=['POST'])
@login_required
@staff_required
def update_payment(sale_id):
    """Update payment for a sale (for credit sales)"""
    sale = Sale.query.get_or_404(sale_id)
    if not current_user.is_admin() and sale.seller_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
        
    data = request.get_json()
    try:
        additional_payment = Decimal(data.get('amount', 0))
        if additional_payment <= 0:
            return jsonify({'error': 'Invalid payment amount'}), 400
            
        sale.amount_paid += additional_payment
        sale.modified_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Payment updated successfully',
            'new_balance': str(sale.balance_due),
            'is_fully_paid': sale.is_fully_paid
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



# RECEIPT/INVOICE DOWNLOAD
@bp.route('/receipt/<int:order_id>')
def view_receipt(order_id):
    order = CustomerOrder.query.get_or_404(order_id)
    payment_option = (order.payment_option or '').lower()
    is_cash = payment_option == 'cash'

    # Group items by brand and model
    grouped = {}
    for item in order.items:
        device = item.device
        price = device.price_cash if is_cash else device.price_credit
        key = f"{device.brand} - {device.model}" 
        if key not in grouped:
            grouped[key] = {
                'name': key,
                'imei': [device.imei],
                'qty': 1,
                'price': price,
                'prices': [price],
                'total': price
            }
        else:
            grouped[key]['imei'].append(device.imei)
            grouped[key]['prices'].append(price)
            grouped[key]['qty'] += 1
            grouped[key]['total'] += price

    receipt = {
        'number': order.id,
        'date': order.created_at.strftime('%Y-%m-%d'),
        'time': order.created_at.strftime('%H:%M'),
        'user': f"{order.assigned_staff.username}" if order.assigned_staff else 'N/A',
        'customer_name': order.customer.full_name,
        'customer_phone': order.customer.phone_number,
        'id_number': order.customer.id_number,
        'items': list(grouped.values()),
        'total': sum(item['total'] for item in grouped.values())
    }

    return render_template('receipt.html', receipt=receipt)




# Download receipt as PDF
@bp.route('/download-receipt/<int:receipt_id>')
def download_receipt_pdf(receipt_id):
    order = CustomerOrder.query.get_or_404(receipt_id)
    payment_option = (order.payment_option or '').lower()
    is_cash = payment_option == 'cash'

    # Group items by brand and model
    grouped = {}
    for item in order.items:
        device = item.device
        price = device.price_cash if is_cash else device.price_credit
        key = f"{device.brand} - {device.model}"

        if key not in grouped:
            grouped[key] = {
                'name': f"{device.brand} - {device.model}",
                'imei': [device.imei],
                'qty': 1,
                'price': price,
                'prices': [price],
                'total': price
            }
        else:
            grouped[key]['imei'].append(device.imei)
            grouped[key]['prices'].append(price)
            grouped[key]['qty'] += 1
            grouped[key]['total'] += price

    receipt = {
        'number': order.id,
        'date': order.created_at.strftime('%Y-%m-%d'),
        'time': order.created_at.strftime('%H:%M'),
        'user': f"{order.assigned_staff.username}" if order.assigned_staff else 'N/A',
        'customer_name': order.customer.full_name,
        'customer_phone': order.customer.phone_number,
        'id_number': order.customer.id_number,
        'items': list(grouped.values()),
        'total': sum(item['total'] for item in grouped.values())
    }

    html = render_template('receipt.html', receipt=receipt, pdf_mode=True)
    pdf = HTML(string=html, base_url=request.base_url).write_pdf()

    return send_file(BytesIO(pdf),
                     download_name=f"receipt_{receipt_id}.pdf",
                     as_attachment=True,
                     mimetype='application/pdf')
