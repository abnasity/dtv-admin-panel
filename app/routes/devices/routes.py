from flask import render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from app.models import Device, User, InventoryTransaction
from app.decorators import admin_required
from app.forms import DeviceForm
from app.routes.devices import bp
from app import db
from slugify import slugify
from app import db
from datetime import datetime

@bp.route('/inventory')
@login_required
def inventory():
    brand = request.args.get('brand')
    status = request.args.get('status')
    imei = request.args.get('imei')
    agent_id = request.args.get('agent')

    # Fetch all staff (for dropdown)
    staff = User.query.filter(User.role == 'staff').all()

    # Base query: exclude deleted devices
    query = Device.query.filter(Device.deleted == False)

    # Apply status filter if selected
    if status:
        query = query.filter(Device.status == status)
    else:
        # Default: include all statuses
        query = query.filter(Device.status.in_(["available", "sold", "transferred"]))

    # Apply brand filter
    if brand:
        query = query.filter(Device.brand == brand)

    # Apply IMEI search
    if imei:
        query = query.filter(Device.imei.ilike(f"%{imei}%"))

    # Apply agent/staff filter
    if agent_id:
        try:
            agent_id = int(agent_id)
            query = query.filter(Device.assigned_staff_id == agent_id)
        except ValueError:
            pass

    # Get filtered devices ordered by newest first
    devices = query.order_by(Device.id.desc()).all()

    # Distinct brand list for dropdown
    brands = [b[0] for b in db.session.query(Device.brand).distinct().all()]

    device_form = DeviceForm()

    return render_template(
        "devices/inventory.html",
        devices=devices,
        device_form=device_form,
        brands=brands,
        staff=staff
    )



#DEVICE DETAIL PAGE

from app.forms import TransferDeviceForm

@bp.route('/devices/<imei>/detail', methods=['GET'])
@login_required
def device_detail_page(imei):
    device = Device.query.filter_by(imei=imei).first_or_404()
    staff_list = User.query.filter_by(role='staff').all()
    form = TransferDeviceForm()
    form.set_staff_choices(staff_list, assigned_staff_id=device.assigned_staff_id)
    return render_template(
        'devices/detail.html',
        device=device,
        staff_list=staff_list,
        form=form
    )






# ADD DEVICE
@bp.route('/device/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_device():
    form = DeviceForm()
    form.set_staff_choices()

    if form.validate_on_submit():
        imei = form.imei.data.strip()  # IMEI required, no fallback to None

        device = Device(
            imei=imei,
            brand=form.brand.data,
            model=form.model.data,
            ram=form.ram.data,
            rom=form.rom.data,
            purchase_price=form.purchase_price.data,
            price_cash=form.price_cash.data,
            assigned_staff_id=form.assigned_staff_id.data,
            status="available"
        )

        db.session.add(device)
        try:
            db.session.commit()
            flash(f'{device.brand} {device.model} added successfully.', 'success')
            return redirect(url_for('devices.inventory'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding device: {e}', 'danger')

    # 👇 Log form errors clearly in terminal
    if form.errors:
        print("⚠️ Form errors:", form.errors)

    return render_template('devices/add.html', form=form)



#TRANSFER DEVICE
@bp.route('/device/<string:imei>/transfer', methods=['GET', 'POST'])
@login_required
@admin_required
def transfer_device(imei):
    device = Device.query.filter_by(imei=imei).first_or_404()
    form = TransferDeviceForm()

    # Staff choices
    all_staff = User.query.filter_by(role='staff').all()
    form.set_staff_choices(all_staff, assigned_staff_id=device.assigned_staff_id)

    if form.validate_on_submit():
        new_staff_id = form.staff_id.data
        new_staff = User.query.get_or_404(new_staff_id)

        if device.assigned_staff_id == new_staff_id:
            flash("Device is already assigned to this staff.", "warning")
            return redirect(url_for('devices.device_detail_page', imei=device.imei))

        # Transfer logic
        device.assigned_staff_id = new_staff_id

        # Do NOT override sold devices
        if device.status != 'sold':
            device.status = 'transferred'

        device.transfer_notes = form.notes.data
        device.transferred_at = datetime.utcnow()

        db.session.commit()

        flash(
            f"Device IMEI {device.imei} successfully transferred to {new_staff.username}.",
            "success"
        )

        return redirect(url_for('devices.device_detail_page', imei=device.imei))

    return render_template('devices/transfer.html', form=form, device=device)






# EDIT DEVICE
@bp.route('/device/<imei>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_device(imei):
    device = Device.query.filter_by(imei=imei).first_or_404()
    form = DeviceForm(original_imei=imei, obj=device)
    form.set_staff_choices()  # Important: avoids "Choices cannot be None"

    if request.method == 'POST':
        form.imei.data = device.imei  # Prevent IMEI change

        if form.validate_on_submit():
            device.brand = form.brand.data
            device.model = form.model.data
            device.ram = form.ram.data
            device.rom = form.rom.data
            device.purchase_price = form.purchase_price.data
            device.price_cash = form.price_cash.data or 0
            device.assigned_staff_id = form.assigned_staff_id.data

            db.session.commit()
            flash("Device updated successfully.", "success")
            return redirect(url_for('devices.inventory'))

    return render_template('devices/edit.html', form=form, device=device)



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


