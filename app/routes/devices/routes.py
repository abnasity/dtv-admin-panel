from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.models import Device
from app.decorators import admin_required
from app.forms import DeviceForm
from app.routes.devices import bp
from app import db

@bp.route('/inventory')
@login_required
def inventory():
    brand = request.args.get('brand')
    status = request.args.get('status')
    imei = request.args.get('imei')

    # Start with a base query
    query = Device.query

    if brand:
        query = query.filter_by(brand=brand)
    if status:
        query = query.filter_by(status=status)
    if imei:
        query = query.filter(Device.imei.ilike(f'%{imei}%'))

    devices = query.order_by(Device.id.desc()).all()

    # For filter dropdowns
    brands = db.session.query(Device.brand).distinct().all()
    brands = [b[0] for b in brands]  # Unpack from tuples

    device_form = DeviceForm()  # Form for add modal

    return render_template(
        'devices/inventory.html',
        devices=devices,
        device_form=device_form,
        brands=brands  # Needed for the Brand dropdown in template
    )
@bp.route('/device/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_device():
    form = DeviceForm()
    if form.validate_on_submit():
        device = Device(
            imei=form.imei.data,
            brand=form.brand.data,
            model=form.model.data,
            ram=form.ram.data,
            rom=form.rom.data,
            purchase_price=form.purchase_price.data,
            price_cash=form.price_cash.data or 0,
            price_credit=form.price_credit.data or 0,
            notes=form.notes.data
        )
        db.session.add(device)
        
        try:
            db.session.commit()
            flash(f'{device.brand} {device.model} added successfully', 'success')
            return redirect(url_for('devices.inventory'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding device: {str(e)}', 'danger')
        
    return render_template('devices/add.html', form=form)

@bp.route('/device/<imei>')
@login_required
def view_device(imei):
    """View device details"""
    device = Device.query.filter_by(imei=imei).first_or_404()
    return render_template('devices/view.html', device=device)

@bp.route('/device/<imei>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_device(imei):
    """Edit device details"""
    device = Device.query.filter_by(imei=imei).first_or_404()
    form = DeviceForm(original_imei=imei, obj=device)
    
    if request.method == 'POST':
        # Ensure IMEI doesn't change
        form.imei.data = device.imei
        
    if form.validate_on_submit():
        device.brand = form.brand.data
        device.model = form.model.data
        device.ram = form.ram.data
        device.rom = form.rom.data
        device.purchase_price = form.purchase_price.data
        device.price_cash = form.price_cash.data or 0
        device.price_credit = form.price_credit.data or 0
        device.notes = form.notes.data
        
        try:
            db.session.commit()
            flash(f'{device.brand} {device.model} updated successfully', 'success')
            return redirect(url_for('devices.inventory'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating device: {str(e)}', 'danger')
    
    return render_template('devices/edit.html', form=form, device=device)
