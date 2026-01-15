from app import db
from app.models import Device, InventoryTransaction

def transfer_device(
    device_id,
    new_staff_id,
    performed_by,
    reason=None
):
    device = Device.query.get_or_404(device_id)

    old_staff_id = device.assigned_staff_id

    if old_staff_id == new_staff_id:
        raise ValueError("Device already assigned to this staff")

    # Log transfer OUT
    if old_staff_id:
        out_tx = InventoryTransaction(
            device_id=device.id,
            staff_id=old_staff_id,
            type="transfer_out",
            notes=reason
        )
        db.session.add(out_tx)

    # Log transfer IN
    in_tx = InventoryTransaction(
        device_id=device.id,
        staff_id=new_staff_id,
        type="transfer_in",
        notes=reason
    )
    db.session.add(in_tx)

    # Update device state
    device.assigned_staff_id = new_staff_id
    device.status = "assigned"

    db.session.commit()
