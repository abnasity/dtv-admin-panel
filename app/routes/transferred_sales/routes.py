from flask import render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from datetime import datetime
from weasyprint import HTML

from app import db
from app.models import Device, Sale, InventoryTransaction
from app.forms import SaleForm
from app.utils.decorators import staff_required
from app.utils.helpers import generate_receipt_number
from app.routes.transferred_sales import bp


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@staff_required
def new_transferred_sale():
    form = SaleForm()
    device = None

    # Fetch all transferred devices
    transferred_devices = Device.query.filter_by(status='transferred').all()
    imeis = [d.imei for d in transferred_devices]

    # Prefill IMEI from query
    imei_query = request.args.get('imei')
    if imei_query:
        imei_query = imei_query.strip()
        form.imei.data = imei_query
        device = Device.query.filter_by(imei=imei_query, status='transferred').first()
    elif len(transferred_devices) == 1:
        form.imei.data = transferred_devices[0].imei
        device = transferred_devices[0]

    if form.validate_on_submit():
        print("Form validated!")  # <-- Add this
    else:
        print("Form errors:", form.errors)  # <-- And this
        
        imei_input = form.imei.data.strip()
        device = Device.query.filter_by(imei=imei_input, status='transferred').first()

        if not device:
            flash(f"Transferred device with IMEI {imei_input} not found.", "danger")
            return render_template(
                'transferred/new.html',
                form=form,
                device=None,
                imeis=imeis,
                is_transferred=True
            )

        staff_id = request.form.get('staff_id', type=int) or current_user.id

        # Create sale
        sale = Sale(
            seller_id=staff_id,
            device_id=device.id,
            customer_name=form.customer_name.data,
            customer_phone=form.customer_phone.data,
            id_number=form.id_number.data,
            sale_price=form.sale_price.data,
            amount_paid=form.sale_price.data,
            payment_type='cash',
            sale_date=datetime.utcnow(),
            shop=current_user.shop if hasattr(current_user, "shop") else form.shop.data
        )
        db.session.add(sale)
        db.session.flush()  # ensures sale.id exists

        # Update device
        device.status = 'sold'
        device.sale_id = sale.id
        device.sold_at = datetime.utcnow()

        # Inventory transaction
        transaction = InventoryTransaction(
            device_id=device.id,
            staff_id=staff_id,
            type='sale',
            notes=f"Transferred device sold to {form.customer_name.data}"
        )
        db.session.add(transaction)
        db.session.commit()

        flash(f"Transferred device IMEI {device.imei} sold successfully!", "success")

        # Generate PDF receipt
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
            'amount_paid': float(sale.amount_paid or 0.0),
            'payment_type': sale.payment_type or "N/A",
            'total': float(sale.sale_price or 0.0),
        }

        html = render_template('receipt.html', receipt=receipt_data)
        pdf = HTML(string=html).write_pdf()

        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=receipt_{sale.id}.pdf'
        return response

    return render_template(
        'transferred/new.html',
        form=form,
        device=device,
        imeis=imeis,
        is_transferred=True
    )
