from flask import url_for
from app.models import Notification, User
from app.extensions import db

def assign_staff_to_order(order):
    """
    Assigns staff member to order based on delivery address.
    
    Args:
        order: The Order object to be assigned
        
    Returns:
        User: The assigned staff member or None if no match found
        
    Side Effects:
        - Updates order.assigned_staff_id
        - Creates notifications for staff and admins
        - Commits changes to database
    """
    try:
        # Input validation
        if not order or not hasattr(order, 'delivery_address'):
            raise ValueError("Invalid order object")

        address = order.delivery_address.strip() if order.delivery_address else None
        print(f"[DEBUG] Delivery address to match: {address}")

        if not address:
            print("[ERROR] No delivery address found.")
            return None

        # Find matching staff
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
            recipient_type='staff',  # Added recipient_type
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
                recipient_type='admin',  # Added recipient_type
                message=admin_message,
                link=url_for('auth.view_order', order_id=order.id)
            )
            db.session.add(admin_notif)

        db.session.flush()  # Commit all at once before final commit
        print(f"[SUCCESS] Order #{order.id} assigned to staff ID: {staff.id} ({staff.username}) and admins notified.")

        return staff

    except Exception as e:
        print(f"[ERROR] Failed to assign staff: {str(e)}")
        db.session.rollback()
        return None

def create_customer_notification(customer_id, message):
    try:
        if not customer_id or not message:
            raise ValueError("Missing required parameters")
            
        notification = Notification(
            user_id=customer_id,
            recipient_type='customer',
            message=message
        )
        db.session.add(notification)
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to create notification: {str(e)}")
        db.session.rollback()
        return False
