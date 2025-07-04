from app.routes.staff import bp
from app.utils.decorators import staff_required
from flask_login import login_required
from flask import render_template, flash, redirect, url_for, request
from app.models import CustomerOrder, User, Notification
from app.extensions import db




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

    #  Get reason from form
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Please provide a reason for failure.', 'warning')
        return redirect(url_for('staff.dashboard'))

    # Mark the order as failed
    order.status = 'failed'
    order.notes = reason  #  Save reason to notes

    # Restock each device in the order
    for item in order.items:
        if item.device and item.device.status != 'available':
            item.device.status = 'available'

    db.session.commit()

    # Notify all admin users
    admin_users = User.query.filter_by(role='admin').all()
    for admin in admin_users:
        notif = Notification(
            user_id=admin.id,
            message=f"Order #{order.id} marked as failed by staff. Reason: {reason}"
        )
        db.session.add(notif)
        
   
      # Notify customer
    if order.customer:
        notif_link_customer = url_for('customers.order_detail', order_id=order.id)
        db.session.add(Notification(
            user_id=order.customer.id,
            message=f"Your order #{order.id}failed. Reason: {reason}",
            recipient_type='customer',
            link=notif_link_customer
        ))

    db.session.commit()

    flash('Order marked as failed. Devices restocked and notifications sent.', 'danger')
    return redirect(url_for('staff.dashboard'))

