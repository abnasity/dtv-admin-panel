from app.routes.staff import bp
from app.utils.decorators import staff_required
from flask_login import login_required, current_user
from flask import render_template, flash, redirect, url_for, request, abort
from app.models import CustomerOrder, User, Notification
from app.extensions import db
from datetime import datetime



# DASHBOARD
@bp.route('/dashboard')
@login_required
@staff_required
def dashboard():
    return render_template('staff/dashboard.html')


# MARK TASK AS FAILED
@bp.route('/orders/<int:order_id>/task_failed', methods=['POST'])
@login_required
@staff_required
def mark_task_failed(order_id):
    order = CustomerOrder.query.get_or_404(order_id)

    if order.status != 'approved':
        flash('Only approved orders can be marked as failed.', 'warning')
        return redirect(url_for('staff.dashboard'))

    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Please provide a reason for failure.', 'warning')
        return redirect(url_for('staff.dashboard'))

    # Mark the order as failed and restock devices
    order.status = 'failed'
    order.notes = f"Marked failed by staff ({current_user.username}) at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}. Reason: {reason}"

    for item in order.items:
        if item.device and item.device.status != 'available':
            item.device.status = 'available'

    # Notify all admins
    admin_users = User.query.filter_by(role='admin').all()
    for admin in admin_users:
        db.session.add(Notification(
            user_id=admin.id,
            recipient_type='admin',
            message=f"Order #{order.id} marked as failed by staff. Reason: {reason}"
        ))

    # Notify customer
    if order.customer:
        notif_link_customer = url_for('customers.order_detail', order_id=order.id)
        db.session.add(Notification(
            customer_id=order.customer.id,
            message=f"Your order #{order.id} failed. Reason: {reason}",
            recipient_type='customer',
            link=notif_link_customer
        ))

    db.session.commit()
    flash('Order marked as failed and notifications sent.', 'danger')
    return redirect(url_for('staff.dashboard'))



# MARK TASK AS SUCCESSFUL
@bp.route('/orders/<int:order_id>/task_success', methods=['POST'])
@login_required
@staff_required
def mark_task_success(order_id):
    order = CustomerOrder.query.get_or_404(order_id)

    if order.status != 'approved':
        flash('Only approved orders can be marked as successful.', 'warning')
        return redirect(url_for('staff.dashboard'))

    # Mark each device in the order as sold
    for item in order.items:
        if item.device and item.device.status != 'sold':
            item.device.mark_as_sold()  # uses your model's mark_as_sold()

    # Optionally, update the order status if needed
    order.status = 'completed'
    order.completed_at = datetime.utcnow()
    print(f"COMPLETED AT being set: {order.completed_at}")
    db.session.commit()
    print(f"After commit: {order.completed_at}")
    # Notify all admins
    admin_users = User.query.filter_by(role='admin').all()
    for admin in admin_users:
        db.session.add(Notification(
            user_id=admin.id,
            recipient_type='admin',
            message=f"Order #{order.id} marked as successful by staff."
        ))

    # Notify the customer
    if order.customer:
        notif_link_customer = url_for('customers.order_detail', order_id=order.id)
        db.session.add(Notification(
            customer_id=order.customer.id,
            message=f"Your order #{order.id} was completed successfully. Thank you for shopping with us!",
            recipient_type='customer',
            link=notif_link_customer
        ))

    db.session.commit()

    flash('Order marked as successful. Device(s) sold and notifications sent.', 'success')
    return redirect(url_for('staff.dashboard'))



# staff sold items
@bp.route('/staff/sold-items')
@login_required
@staff_required
def view_sold_items():
    sold_items = CustomerOrder.query.filter_by(
        assigned_staff_id=current_user.id,
        status='completed'
    ).filter(CustomerOrder.completed_at.isnot(None)) .order_by(CustomerOrder.completed_at.desc()).all() 
    return render_template('staff/sold_items.html', sold_items=sold_items)



# FAILED ORDERS
@bp.route('/staff/failed-orders')
@login_required
@staff_required
def view_failed_orders():
    failed_orders = CustomerOrder.query.filter_by(
        status='failed',
        assigned_staff_id=current_user.id
    ).all()
    return render_template('staff/failed_orders.html', failed_orders=failed_orders)

