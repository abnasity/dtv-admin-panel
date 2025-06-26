from app.models import User
from app.extensions import db

def assign_staff_to_order(order):
    from app.models import User
    from app.extensions import db

    print(f"[DEBUG] Delivery address: {order.delivery_address}")

    if not order.delivery_address:
        print("[ERROR] No delivery address found.")
        return None

    # Find staff with matching address
    staff = User.query.filter_by(role='staff', address=order.delivery_address).first()
    
    if not staff:
        print(f"[WARNING] No staff found for address: {order.delivery_address}")
        return None

    print(f"[INFO] Staff found: {staff.username} (ID: {staff.id})")
    
    # Assign staff
    order.assigned_staff_id = staff.id

    # Make sure SQLAlchemy tracks the change
    db.session.add(order)
    db.session.flush()  # Force flush to DB (optional, before commit)

    print(f"[SUCCESS] Order #{order.id} assigned to staff ID: {order.assigned_staff_id}")

    return staff

