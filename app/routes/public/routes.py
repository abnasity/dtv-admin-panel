from flask import render_template, request, session, url_for, flash, redirect, abort
from flask_login import login_required, current_user
from datetime import datetime
from app.routes.public import bp
from app.models import Device, CartItem, Customer, CustomerOrder, CustomerOrderItem
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


# VIEW CART
@bp.route('/cart')
@login_required
def view_cart():
    if not isinstance(current_user, Customer):
        abort(403)

    cart_items = CartItem.query.filter_by(customer_id=current_user.id).all()
    return render_template('customers/cart.html', cart_items=cart_items)


# REMOVE FROM CART
@bp.route('/remove-from-cart/<int:device_id>', methods=['POST'])
def remove_from_cart(device_id):
    if current_user.is_authenticated and isinstance(current_user, Customer):
        CartItem.query.filter_by(customer_id=current_user.id, device_id=device_id).delete()
        db.session.commit()
        flash("Item removed from cart.", "info")
    else:
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

    cart_items = CartItem.query.filter_by(customer_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty.", "info")
        return redirect(url_for('public.view_cart'))

    devices = [Device.query.get(item.device_id) for item in cart_items]
    total_price = sum(float(d.purchase_price) for d in devices if d)
    form = CheckoutForm()

    return render_template('public/checkout.html', products=devices, total_price=total_price, form=form)

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

    cart_items = CartItem.query.filter_by(customer_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('public.cart'))

    # Create order
    order = CustomerOrder(customer_id=current_user.id)
    db.session.add(order)
    db.session.flush()  # get order.id before committing

    for item in cart_items:
        device = Device.query.get(item.device_id)
        if not device or device.status != 'available':
            continue
        
        device.mark_as_sold()

        order_item = CustomerOrderItem(
            customer_order_id=order.id,
            device_id=device.id,
            unit_price=device.purchase_price  # or sale_price if you have it
        )
        db.session.add(order_item)

    # Clear cart
    CartItem.query.filter_by(customer_id=current_user.id).delete()

    db.session.commit()
    flash("Your order has been placed successfully!", "success")
    return redirect(url_for('public.order_success'))


# SUCCESSFUL ORDER
@bp.route('/order-success')
@login_required
def order_success():
    if not isinstance(current_user, Customer):
        abort(403)
    return render_template('public/order_success.html')
