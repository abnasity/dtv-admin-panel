from flask import url_for
from app.models import Notification, User
from app.extensions import db

def assign_staff_to_order(order):
    address = order.delivery_address.strip() if order.delivery_address else None
    print(f"[DEBUG] Delivery address to match: {address}")

    if not address:
        print("[ERROR] No delivery address found.")
        return None

    staff = User.query.filter_by(role='staff', address=address).first()
    
    if not staff:
        print(f"[WARNING] No staff found for address: '{address}'")
        return None

    # Assign staff to the order
    order.assigned_staff_id = staff.id
    db.session.add(order)

    # Notify the staff
    staff_message = f"You have been assigned to order #{order.id}."
    staff_notif = Notification(
        user_id=staff.id,
        message=staff_message,
        link=url_for('auth.view_order_staff', order_id=order.id)
    )
    db.session.add(staff_notif)

    # Notify all admins
    admin_users = User.query.filter_by(role='admin').all()
    for admin in admin_users:
        admin_message = f"New order placed by {order.customer.full_name}, assigned to {staff.username}."
        admin_notif = Notification(
            user_id=admin.id,
            message=admin_message,
            link=url_for('auth.view_order', order_id=order.id)
        )
        db.session.add(admin_notif)

    db.session.flush()  # Commit all at once before final commit
    print(f"[SUCCESS] Order #{order.id} assigned to staff ID: {staff.id} ({staff.username}) and admins notified.")

    return staff
