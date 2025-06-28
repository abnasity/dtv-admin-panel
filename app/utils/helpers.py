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

    # Assign staff to order
    order.assigned_staff_id = staff.id
    db.session.add(order)

    # Add notification
    message = f"You have been assigned to order #{order.id}."
    notif = Notification(staff_id=staff.id, message=message)
    db.session.add(notif)

    # Commit after both are added
    db.session.flush()
    print(f"[SUCCESS] Order #{order.id} assigned to staff ID: {staff.id} ({staff.username})")

    return staff
