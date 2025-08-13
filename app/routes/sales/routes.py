from flask import render_template, redirect, url_for, flash, request, jsonify, make_response, Response, send_file, abort
from flask_login import login_required, current_user
from app.models import Device, Sale
from app.forms import SaleForm
from app.routes.sales import bp
from app.utils.decorators import staff_required
from app.utils.helpers import generate_receipt_number
from app import db
from decimal import Decimal
from datetime import datetime
from xhtml2pdf import pisa
from io import BytesIO
import base64
import os
from flask import current_app
from collections import defaultdict
import imgkit
import io



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
    imei = request.args.get('imei')

    if imei:
        form.imei.data = imei

    if form.validate_on_submit():
        device = Device.query.filter_by(imei=form.imei.data, status='available').first()
        if not device:
            flash('Device not found or not available', 'danger')
            return render_template('sales/new.html', form=form)

        try:
            # Create sale
            sale = Sale(
                device=device,
                seller=current_user,
                sale_price=form.sale_price.data,
                payment_type=form.payment_type.data,
                amount_paid=form.amount_paid.data,
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

    return render_template('sales/new.html', form=form)




# COMPLETE SALE
@bp.route('/sales/complete', methods=['GET', 'POST'])
@login_required
def complete_sale():
    form = SaleForm()

    if form.validate_on_submit():
        # Check if device exists and is available
        device = Device.query.filter_by(imei=form.imei.data).first()
        if not device:
            form.imei.errors.append('Device with this IMEI not found in inventory.')
            return render_template('sales/new_sale.html', form=form)

        # Create the sale record
        sale = Sale(
            seller_id=current_user.id,
            customer_name=form.customer_name.data,
            customer_phone=form.customer_phone.data,
            id_number=form.id_number.data,
            device_id=device.id,
            sale_price=form.sale_price.data,
            amount_paid=form.amount_paid.data,
            payment_type=form.payment_type.data,
            sale_date=datetime.utcnow()
        )
        db.session.add(sale)
        db.session.commit()  # sale.id now available

        # Redirect to separate download route
        return redirect(url_for('sales.download_receipt_image', sale_id=sale.id))

    return render_template('sales/new.html', form=form)

# DOWNLOAD RECEIPT
@bp.route('/download-receipt-image/<int:sale_id>')
@login_required
def download_receipt_image(sale_id):
    sale = Sale.query.get_or_404(sale_id)

    if not current_user.is_admin() and sale.seller_id != current_user.id:
        abort(403)

    receipt_data = {
        'sale_id': sale.id,
        'number': generate_receipt_number(),
        'date': sale.sale_date.strftime('%Y-%m-%d'),
        'time': sale.sale_date.strftime('%H:%M'),
        'user': sale.seller.username,
        'customer_name': sale.customer_name,
        'customer_phone': sale.customer_phone,
        'id_number': sale.id_number,
        'brand': sale.device.brand,
        'device': sale.device.model,
        'ram': sale.device.ram,
        'storage': sale.device.rom,
        'imei': sale.device.imei,
        'sale_price': float(sale.sale_price),
        'amount_paid': float(sale.amount_paid),
        'payment_type': sale.payment_type,
        'total': float(sale.sale_price),
    }

    html = render_template('receipt.html', receipt=receipt_data)
    img_bytes = imgkit.from_string(html, False, options={'format': 'png'})

    return send_file(
        io.BytesIO(img_bytes),
        mimetype='image/png',
        as_attachment=True,
        download_name=f"receipt_{sale.id}.png"
    )




@bp.route('/sales/<int:sale_id>/complete', methods=['POST'])
@login_required
@staff_required
def complete_sale_api(sale_id):
    """Mark a sale as fully paid/completed."""
    sale = Sale.query.get_or_404(sale_id)

    # Ensure the user has permission
    if not current_user.is_admin() and sale.seller_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403

    try:
        # Mark as fully paid
        sale.amount_paid = sale.sale_price
        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route("/create-sale", methods=["POST"])
@login_required
def create_sale():
    # 1. Process sale logic
    sale = Sale(...)
    db.session.add(sale)
    db.session.commit()

    # 2. Generate the receipt image
    generate_receipt_image(sale)  # your custom function

    # 3. Redirect to download route
    return redirect(url_for("download_receipt_image", sale_id=sale.id))


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




