from datetime import datetime
from app.models import Receipt
from sqlalchemy import func

def generate_receipt_number():
    today_str = datetime.now().strftime('%Y%m%d')
    today_date = datetime.now().date()

    # Count how many receipts already exist for today
    count = Receipt.query.filter(func.date(Receipt.date) == today_date).count() + 1

    # Format the receipt number
    return f"DTV-{today_str}-{count:03d}"
