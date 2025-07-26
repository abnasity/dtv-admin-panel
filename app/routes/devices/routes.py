from flask import render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app.models import Device, DeviceSpecs
from app.decorators import admin_required
from app.forms import DeviceForm, DeviceSpecsForm
from app.routes.devices import bp
from app import db
from slugify import slugify
from cloudinary.uploader import upload
from app.utils.cloudinary_utils import init_cloudinary

@bp.route('/inventory')
@login_required
def inventory():
    brand = request.args.get('brand')
    status = request.args.get('status')
    imei = request.args.get('imei')

    # Start with a base query
    query = Device.query.filter(Device.featured == False, Device.deleted == False)

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
    specs_form = DeviceSpecsForm()
    


    return render_template(
        'devices/inventory.html',
        devices=devices,
        device_form=device_form,
        specs_form=specs_form,
        brands=brands  # Needed for the Brand dropdown in template
    )
    
# GET OR CREATE SPECS
def get_or_create_specs(spec_data):
    existing = DeviceSpecs.query.filter_by(
        os=spec_data['os'],
        chipset=spec_data['chipset'],
        display_size=spec_data['display_size'],
        main_camera=spec_data['main_camera']
    ).first()
    if existing:
        return existing
    new_specs = DeviceSpecs(**spec_data)
    db.session.add(new_specs)
    db.session.commit()
    return new_specs
 

# ADD DEVICE
@bp.route('/device/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_device():
    form = DeviceForm()
    specs_form = DeviceSpecsForm()

    # Prefill only on GET request
    if request.method == 'GET':
        specs_form.details.data = """\
• RAM:
• Storage:
• Battery:
• Processor:
• Rear Camera:
• Front Camera:
• Display:
• Network:
• OS:
• Charging:
• Fingerprint:
• Ports:
• Extras:
"""

    if form.validate_on_submit() and specs_form.validate_on_submit():
        # Generate unique slug
        base_slug = slugify(f"{form.brand.data} {form.model.data}")
        slug = base_slug
        counter = 1
        while Device.query.filter(Device.slug.ilike(slug)).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        imei = form.imei.data.strip() if form.imei.data else None

        device = Device(
            imei=imei if not form.featured.data else None,
            brand=form.brand.data,
            model=form.model.data,
            slug=slug,
            ram=form.ram.data,
            rom=form.rom.data,
            purchase_price=form.purchase_price.data,
            price_cash=form.price_cash.data or 0,
            price_credit=form.price_credit.data or 0,
            featured=form.featured.data,
            description=form.description.data or specs_form.details.data,
            notes=form.notes.data,
            status='featured' if form.featured.data else 'available'
        )

        # 🔐 Secure Cloudinary Upload
        if form.image.data:
            try:
                from app.utils.cloudinary_utils import generate_signature
                import time
                import os

                timestamp = int(time.time())
                params = {
                    'folder': 'devices',
                    'overwrite': True,
                    'timestamp': timestamp
                }
                signature = generate_signature(params)

                result = upload(
                    form.image.data,
                    folder="devices",
                    overwrite=True,
                    timestamp=timestamp,
                    api_key=os.getenv("CLOUDINARY_API_KEY"),
                    signature=signature
                )

                device.main_image = result.get('secure_url')
            except Exception as e:
                flash(f"Image upload failed: {str(e)}", 'warning')

        # Attach specs
        device.specs = DeviceSpecs(details=specs_form.details.data.strip())

        db.session.add(device)
        try:
            db.session.commit()
            flash(f'{device.brand} {device.model} added successfully', 'success')
            return redirect(url_for('devices.inventory'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding device: {str(e)}', 'danger')

    return render_template('devices/add.html', form=form, specs_form=specs_form)



# EDIT DEVICE
@bp.route('/device/<imei>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_device(imei):
    device = Device.query.filter_by(imei=imei).first_or_404()
    form = DeviceForm(original_imei=imei, obj=device)
    specs_form = DeviceSpecsForm(obj=device.specs)

    if request.method == 'POST':
        form.imei.data = device.imei  # Prevent IMEI change

        if form.validate_on_submit() and specs_form.validate_on_submit():
            device.brand = form.brand.data
            device.model = form.model.data
            device.ram = form.ram.data
            device.rom = form.rom.data
            device.purchase_price = form.purchase_price.data
            device.price_cash = form.price_cash.data or 0
            device.price_credit = form.price_credit.data or 0
            device.notes = form.notes.data
            device.featured = form.featured.data

            # 🔐 Cloudinary Image Upload
            if form.image.data:
                try:
                    from app.utils.cloudinary_utils import generate_signature
                    import time
                    import os

                    timestamp = int(time.time())
                    params = {
                        'folder': 'devices',
                        'overwrite': True,
                        'timestamp': timestamp
                    }
                    signature = generate_signature(params)

                    result = upload(
                        form.image.data,
                        folder="devices",
                        overwrite=True,
                        timestamp=timestamp,
                        api_key=os.getenv("CLOUDINARY_API_KEY"),
                        signature=signature
                    )

                    device.main_image = result.get('secure_url')
                except Exception as e:
                    flash(f"Image upload failed: {str(e)}", 'warning')

            # Update specs
            if device.specs:
                device.specs.details = specs_form.details.data
            else:
                device.specs = DeviceSpecs(details=specs_form.details.data)

            try:
                db.session.commit()
                flash(f'{device.brand} {device.model} updated successfully', 'success')
                return redirect(url_for('devices.inventory'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating device: {str(e)}', 'danger')

    return render_template('devices/edit.html', form=form, specs_form=specs_form, device=device)


# DELETE DEVICE
@bp.route('/devices/<int:device_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_inventory(device_id):
    if not current_user.is_admin():
        flash("Unauthorized", "danger")
        return redirect(url_for('public.home'))

    device = Device.query.get_or_404(device_id)
    device.deleted = True  # ← Soft delete instead of real delete
    db.session.commit()
    flash(f"Device '{device.brand} {device.model}' has been deleted.", "success")

    return redirect(url_for('devices.inventory'))

# DELETED INVENTORY
@bp.route('/inventory/deleted')
@login_required
@admin_required
def deleted_inventory():
    devices = Device.query.filter_by(deleted=True).order_by(Device.id.desc()).all()
    return render_template('devices/deleted_inventory.html', devices=devices)

# RESTORE DELETED INVENTORY
@bp.route('/devices/<int:device_id>/restore', methods=['POST'])
@login_required
@admin_required
def restore_device(device_id):
    device = Device.query.get_or_404(device_id)
    device.deleted = False
    db.session.commit()
    flash(f"Device '{device.brand} {device.model}' has been restored.", "success")
    return redirect(url_for('devices.deleted_inventory'))

# DELETE INVENTORY PERMANENTLY
# PERMANENT DELETE DEVICE
@bp.route('/devices/<int:device_id>/permanent-delete', methods=['POST'])
@login_required
@admin_required
def permanently_delete_device(device_id):
    device = Device.query.get_or_404(device_id)

    if not device.deleted:
        flash("Device must be soft-deleted first before permanent deletion.", "warning")
        return redirect(url_for('devices.inventory'))

    # Delete associated records first if applicable (e.g., specs, order items, etc.)
    if device.specs:
        db.session.delete(device.specs)

    db.session.delete(device)
    db.session.commit()

    flash(f"Device '{device.brand} {device.model}' has been permanently deleted.", "danger")
    return redirect(url_for('devices.deleted_inventory'))




# LEARN MORE
@bp.route('/learn_more/<device_slug>')
def learn_more_device(device_slug):
    device = Device.query.filter_by(slug=device_slug).first_or_404()
    
    specs = {}
    if device.specs:
        for col in device.specs.__table__.columns:
            if col.name in ['id', 'device_id', 'created_at', 'updated_at']:
                continue
            value = getattr(device.specs, col.name)
            if value:
                label = col.name.replace('_', ' ').title()
                specs[label] = value
    
    
    return render_template('learn_more/details.html', device=device, specs=specs)


# SCAN IMEI
@bp.route('/scan/device')
@login_required
def scan_device():
    imei = request.args.get('imei', '').strip()
    device = Device.query.filter_by(imei=imei).first()

    if not device:
        return jsonify(success=False, message="Device not found")

    return jsonify(success=True, device={
        'imei': device.imei,
        'brand': device.brand,
        'model': device.model,
        'price_cash': device.price_cash,
        'status': device.status,
        'description': device.description
    })
    
# SCANNER ROUTE  
@bp.route('/devices/scan')
@login_required
def scan_page():
    return render_template('devices/barcode_scanner.html')


# VIEW DEVICE AFTER SCANNING
@bp.route('/device/<imei>')
def view_device_by_imei(imei):
    print(f"🔍 Requested IMEI: {imei}")
    imei = imei.strip()
    device = Device.query.filter(db.func.trim(Device.imei) == imei).first()

    if not device:
        flash("Device not found or IMEI mismatch", "warning")
        return redirect(url_for('auth.scan_page'))

    return render_template('devices/device_output.html', device=device)


