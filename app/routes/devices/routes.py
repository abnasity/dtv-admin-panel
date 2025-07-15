from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required
from app.models import Device, DeviceSpecs
from app.decorators import admin_required
from app.forms import DeviceForm, DeviceSpecsForm
from app.routes.devices import bp
from app import db
from slugify import slugify

@bp.route('/inventory')
@login_required
def inventory():
    brand = request.args.get('brand')
    status = request.args.get('status')
    imei = request.args.get('imei')

    # Start with a base query
    query = Device.query.filter(Device.featured == False)

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

    if form.validate_on_submit() and specs_form.validate_on_submit():
        # Slug generation with uniqueness check
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
            notes=form.notes.data
        )

        device.status = 'featured' if form.featured.data else 'available'
        if form.image.data:
            try:
                filename = device.add_image(form.image.data)
                device.main_image = filename
            except Exception as e:
                flash(f"Image upload failed: {str(e)}", 'warning')

        if not specs_form.details.data:
            flash("Please provide full specifications.", "warning")
            return render_template('devices/add.html', form=form, specs_form=specs_form)

        device.specs = DeviceSpecs(details=specs_form.details.data)
        
        db.session.add(device)

        try:
            db.session.commit()
            flash(f'{device.brand} {device.model} added successfully', 'success')
            return redirect(url_for('devices.inventory'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding device: {str(e)}', 'danger')

    return render_template('devices/add.html', form=form, specs_form=specs_form)


# VIEW DEVICE
@bp.route('/device/<imei>')
@login_required
def view_device(imei):
    """View device details"""
    device = Device.query.filter_by(imei=imei).first_or_404()
    return render_template('devices/view.html', device=device)

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

            # Handle image upload
            if form.image.data:
                try:
                    filename = device.add_image(form.image.data)
                    device.main_image = filename
                except Exception as e:
                    flash(f"Image upload failed: {str(e)}", 'warning')

            # Update or set specs
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


# FEATURED DEVICES
@bp.route('/devices/featured')
@admin_required
def featured_devices():
    devices = Device.query.filter_by(featured=True).all()
    return render_template('devices/featured.html', devices=devices)


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



