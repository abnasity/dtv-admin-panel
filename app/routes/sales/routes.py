from flask import render_template, redirect, url_for, flash, request, jsonify, make_response, Response, send_file, abort
from flask_login import login_required, current_user
from app.models import Device, Sale, User, InventoryTransaction
from app.forms import SaleForm
from app.routes.sales import bp
from app.utils.decorators import staff_required
from app.utils.helpers import generate_receipt_number
from app import db
from decimal import Decimal
from datetime import datetime
from io import BytesIO
import base64
import os
from flask import current_app
from collections import defaultdict
import io
from weasyprint import HTML
from flask import make_response



@bp.route('/sales')
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
    form = SaleForm()
    device = None  # <-- ADD THIS LINE
    imei = request.args.get('imei')

    if imei:
        form.imei.data = imei
        # Optionally prefetch device for display:
        device = Device.query.filter_by(imei=imei).first()

    if form.validate_on_submit():
        device = Device.query.filter_by(imei=form.imei.data, status='available').first()
        if not device:
            flash('Device not found or not available', 'danger')
            return render_template('sales/new.html', form=form, device=device)

        try:
            sale = Sale(
                device=device,
                seller=current_user,
                sale_price=form.sale_price.data,
                payment_type='cash',
                amount_paid=form.sale_price.data,
                shop=form.shop.data,
                notes=form.notes.data
            )
            device.mark_as_sold()
            db.session.add(sale)
            db.session.commit()

            flash('Sale recorded successfully!', 'success')
            return redirect(url_for('sales.sale_detail', sale_id=sale.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error recording sale: {str(e)}', 'danger')

    return render_template('sales/new.html', form=form, device=device)


# Merge imei to sale details
@bp.route('/sales/check_imei/<imei>')
@login_required
def check_imei(imei):
    """AJAX route to check device availability and assigned staff"""
    device = Device.query.filter_by(imei=imei.strip()).first()

    if not device:
        return jsonify({'found': False, 'message': 'Device not found in inventory.'})

    if device.status.lower() == 'sold':
        return jsonify({'found': False, 'message': 'Device is already sold.'})

    return jsonify({
        'found': True,
        'brand': device.brand,
        'model': device.model,
        'ram': device.ram,
        'rom': device.rom,
        'selling_price': float(device.price_cash or 0),
        # the same logic that works in the device details page
        'assigned_staff': device.assigned_staff.username if device.assigned_staff else 'Not assigned',
        'assigned_staff_id': device.assigned_staff.id if device.assigned_staff else None
    })


# COMPLETE SALE
@bp.route('/sales/complete', methods=['GET', 'POST'])
@login_required
def complete_sale():
    form = SaleForm()
    device = None  # define for template use

    if form.validate_on_submit():
        imei = form.imei.data.strip()
        device = Device.query.filter_by(imei=imei).first()

        if not device:
            flash('Device not found in inventory.', 'danger')
            return render_template('sales/complete_sale.html', form=form)

        if device.status.lower() == "sold":
            flash('This device is already sold.', 'danger')
            return render_template('sales/complete_sale.html', form=form)

        # ✅ Create the sale
        sale = Sale(
            seller_id=device.assigned_staff.id if device.assigned_staff else current_user.id,
            customer_name=form.customer_name.data,
            customer_phone=form.customer_phone.data,
            id_number=form.id_number.data,
            device_id=device.id,
            sale_price=form.sale_price.data,
            amount_paid=form.sale_price.data,
            payment_type='cash',
            sale_date=datetime.utcnow(),
            shop=current_user.shop if hasattr(current_user, 'shop') else form.shop.data
        )

        # ✅ Mark device as sold
        device.status = 'sold'

        # ✅ Log transaction
        transaction = InventoryTransaction(
            device_id=device.id,
            staff_id=device.assigned_staff_id or current_user.id,
            type='sale',
            notes=f"Device sold to {form.customer_name.data}"
        )

        db.session.add_all([sale, transaction])
        db.session.commit()

        flash('Sale recorded successfully.', 'success')
        return redirect(url_for('sales.sale_details', sale_id=sale.id))

    return render_template('sales/complete_sale.html', form=form, device=device)



# SALE DETAILS
@bp.route("/sales/<int:sale_id>/details")
@login_required
def sale_details(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    return render_template("sales/details.html", sale=sale)


# DOWNLOAD RECEIPT
@bp.route('/download-receipt-image/<int:sale_id>')
@login_required
def download_receipt_image(sale_id):
    sale = Sale.query.get_or_404(sale_id)

    # Only admin or seller can access
    if not current_user.is_admin() and sale.seller_id != current_user.id:
        abort(403)

    # Handle missing payment type or amount_paid safely
    payment_type = sale.payment_type or "Not specified"
    amount_paid = float(sale.amount_paid or 0.0)

    receipt_data = {
        'sale_id': sale.id,
        'number': generate_receipt_number(),
        'date': sale.sale_date.strftime('%Y-%m-%d'),
        'time': sale.sale_date.strftime('%H:%M'),
        'user': sale.seller.username if sale.seller else "Unknown",
        'customer_name': sale.customer_name or "N/A",
        'customer_phone': sale.customer_phone or "N/A",
        'id_number': sale.id_number or "N/A",
        'brand': sale.device.brand if sale.device else "N/A",
        'device': sale.device.model if sale.device else "N/A",
        'ram': sale.device.ram if sale.device else "N/A",
        'storage': sale.device.rom if sale.device else "N/A",
        'imei': sale.device.imei if sale.device else "N/A",
        'sale_price': float(sale.sale_price or 0.0),
        'amount_paid': amount_paid,
        'payment_type': payment_type,
        'total': float(sale.sale_price or 0.0),
    }

    html = render_template('receipt.html', receipt=receipt_data)
    pdf = HTML(string=html).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=receipt_{sale.id}.pdf'
    return response

# COMPLETE SALE
@bp.route('/sales/<int:sale_id>/complete', methods=['POST'])
@login_required
@staff_required
def complete_sale_api(sale_id):
    sale = Sale.query.get_or_404(sale_id)

    if not current_user.is_admin() and sale.seller_id != current_user.id:
        return jsonify(success=False, error='Permission denied'), 403

    if sale.status != 'pending':
        return jsonify(success=False, error='Sale cannot be completed'), 400

    try:
        sale.amount_paid = sale.sale_price
        sale.status = 'completed'
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500


# CREATE SALE
@bp.route("/create-sale", methods=["POST"])
@login_required
def create_sale():
    # 1. Process sale logic
    sale = Sale(...)
    db.session.add(sale)
    db.session.commit()


    # 3. Redirect to download route
    return redirect(url_for("download_receipt_image", sale_id=sale.id))



# GET DEVICE
@bp.route('/device/<imei>', methods=['GET'])
@login_required
@staff_required
def get_device(imei):
    """Get device details by IMEI for sale"""
    device = Device.query.filter_by(imei=imei, status='available').first()
    if not device:
        return jsonify({'error': 'Device not found or not available'}), 404
    return jsonify(device.to_dict())

# SALE DETAIL
@bp.route('/detail/<int:sale_id>')
@login_required
def sale_detail(sale_id):
    """Show sale details"""
    sale = Sale.query.get_or_404(sale_id)
    if not current_user.is_admin() and sale.seller_id != current_user.id:
        flash('You do not have permission to view this sale.', 'error')
        return redirect(url_for('sales.index'))
    return render_template('sales/detail.html', sale=sale)

# UPDATE PAYMENT
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
    # Fetch the order from the database
    from app.models import Order  # Make sure Order is imported at the top if not already
    order = Order.query.get_or_404(order_id)

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




