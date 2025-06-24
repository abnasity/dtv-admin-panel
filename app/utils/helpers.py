from app.models import User
from app.extensions import db
def assign_staff_to_customer(customer):
    if not customer.address:
        return None  # Skip if address not provided

    staff = User.query.filter_by(role='staff', address=customer.address).first()
    if staff:
        customer.assigned_staff = staff
        db.session.commit()
        return staff
    return None
