from flask import render_template, request, session, url_for, flash, redirect, abort
from flask_login import login_required, current_user
from datetime import datetime
from app.routes.public import bp
from app.models import Device, CartItem, Customer, SaleItem, Sale
from app.forms import CheckoutForm
from app import db

# PUBLIC ROUTE
@bp.route('/public')
@bp.route('/')
def home():
    return render_template('public/home.html', public_view=True)
    
# PUBLIC SEARCH ROUTE 
@bp.route('/search')
def search():
    query = request.args.get('query', '')
    products = Device.query.filter(
        Device.model.ilike(f"%{query}%") |
        Device.brand.ilike(f"%{query}%")
    ).all()
    return render_template('customers/dashboard.html', products=products)



# ADD TO CART
@bp.route('/add-to-cart/<int:device_id>', methods=['POST'])
def add_to_cart(device_id):
    device = Device.query.get_or_404(device_id)

    if current_user.is_authenticated and isinstance(current_user, Customer):
        # FIX: Filter by both device AND customer
        exists = CartItem.query.filter_by(customer_id=current_user.id, device_id=device_id).first()
        if exists:
            flash("Item already in cart.", "info")
        else:
            db.session.add(CartItem(customer_id=current_user.id, device_id=device.id))
            db.session.commit()
            flash(f"{device.brand} {device.model} added to cart!", "success")
    else:
        # Anonymous users - session-based cart
        cart = session.get('cart', [])
        if device_id in cart:
            flash("Item already in cart.", "info")
        else:
            cart.append(device_id)
            session['cart'] = cart
            flash(f"{device.brand} {device.model} added to cart!", "success")

    return redirect(request.referrer or url_for('public.home'))



# CART VIEW
@bp.route('/cart')
def view_cart():
    cart_ids = session.get('cart', [])
    products = Device.query.filter(Device.id.in_(cart_ids)).all()
    return render_template('public/cart.html', products=products)

# REMOVE FROM CART
@bp.route('/remove-from-cart/<int:device_id>', methods=['POST'])
def remove_from_cart(device_id):
    cart = session.get('cart', [])
    if device_id in cart:
        cart.remove(device_id)
        session['cart'] = cart
        flash("Item removed from cart.", "info")
    else:
        flash("Item not found in cart.", "warning")
    return redirect(url_for('public.view_cart'))

# PROCEED TO CHECKOUT
@bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if not isinstance(current_user, Customer):
        flash("Only customers can checkout.", "danger")
        return redirect(url_for('public.view_cart'))

    cart_ids = session.get('cart', [])
    if not cart_ids:
        flash("Your cart is empty.", "info")
        return redirect(url_for('public.view_cart'))

    devices = Device.query.filter(Device.id.in_(cart_ids)).all()
    total_price = sum(float(d.sale_price or d.purchase_price) for d in devices)
    form = CheckoutForm()

    return render_template(
        'public/checkout.html',
        products=devices,
        total_price=total_price,
        form=form
    )


# PLACING AN ORDER
@bp.route('/place_order', methods=['POST'])
@login_required
def place_order():
    if not isinstance(current_user, Customer):
        abort(403)

    form = CheckoutForm()

    if not form.validate_on_submit():
        flash("Please fill the form correctly.", "danger")
        return redirect(url_for('public.checkout'))

    cart_ids = session.get('cart', [])
    if not cart_ids:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('public.cart'))

    devices = Device.query.filter(Device.id.in_(cart_ids), Device.status == 'available').all()
    if not devices:
        flash("No available devices found in your cart.", "danger")
        return redirect(url_for('public.cart'))

    payment_type = form.payment_type.data
    amount_paid = float(form.amount_paid.data)

    for device in devices:
        if device.status != 'available':
            continue

        sale_price = float(device.sale_price or device.purchase_price)
        sale = Sale(
            device_id=device.id,
            customer_id=current_user.id,
            sale_price=sale_price,
            amount_paid=min(amount_paid, sale_price),
            payment_type=payment_type,
            seller_id=None
        )
        device.mark_as_sold()
        db.session.add(sale)

    db.session.commit()
    session.pop('cart', None)
    flash("Your order has been placed successfully!", "success")
    return redirect(url_for('public.order_success'))


# SUCCESSFUL ORDER
@bp.route('/order-success')
@login_required
def order_success():
    if not isinstance(current_user, Customer):
        abort(403)
    return render_template('public/order_success.html')
