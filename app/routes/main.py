from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.models import Sale, Device
from app import db
from app.decorators import admin_required
from sqlalchemy import func
from datetime import datetime, timedelta

bp = Blueprint('main', __name__)

def calculate_growth_rate(days=30):
    """Calculate sales growth rate comparing two periods"""
    current_period_end = datetime.utcnow()
    current_period_start = current_period_end - timedelta(days=days)
    previous_period_start = current_period_start - timedelta(days=days)
    
    current_sales = db.session.query(func.count(Sale.id)).filter(
        Sale.sale_date.between(current_period_start, current_period_end)
    ).scalar() or 0
    
    previous_sales = db.session.query(func.count(Sale.id)).filter(
        Sale.sale_date.between(previous_period_start, current_period_start)
    ).scalar() or 0
    
    if previous_sales == 0:
        return 100 if current_sales > 0 else 0
        
    growth_rate = ((current_sales - previous_sales) / previous_sales) * 100
    return round(growth_rate, 1)

@bp.route('/')
@login_required
def index():
    if current_user.is_admin():
        return dashboard()
    return render_template('devices/inventory.html')

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get date range from query parameters (default 30 days)
    days = int(request.args.get('days', 30))
    date_from = datetime.utcnow() - timedelta(days=days)
    
    # Get sales metrics
    sales_data = db.session.query(
        func.count(Sale.id).label('total_sales'),
        func.sum(Sale.sale_price).label('total_revenue'),
        func.sum(Sale.amount_paid).label('total_collected')
    ).filter(Sale.sale_date >= date_from).first()
    
    # Get inventory metrics
    inventory_data = db.session.query(
        func.count(Device.id).label('total_devices'),
        func.count(Device.id).filter(Device.status == 'available').label('available_devices')
    ).first()
    
    # Get outstanding credit
    credit_data = db.session.query(
        func.sum(Sale.sale_price - Sale.amount_paid).label('outstanding_credit')
    ).filter(Sale.payment_type == 'credit').first()
    
    # Get sales trend data (daily)
    trend_data = db.session.query(
        func.date(Sale.sale_date).label('date'),
        func.count(Sale.id).label('sales_count')
    ).filter(
        Sale.sale_date >= date_from
    ).group_by(
        func.date(Sale.sale_date)
    ).order_by('date').all()
    
    # Get payment type breakdown
    payment_data = db.session.query(
        Sale.payment_type,
        func.count(Sale.id).label('count')
    ).filter(
        Sale.sale_date >= date_from
    ).group_by(Sale.payment_type).all()
    
    # Get recent sales
    recent_sales = Sale.query.order_by(Sale.sale_date.desc()).limit(5).all()
    
    # Get top selling products
    top_products = db.session.query(
        Device.brand,
        Device.model,
        func.count(Sale.id).label('total_sold'),
        func.sum(Sale.sale_price).label('revenue')
    ).join(Sale).group_by(
        Device.brand,
        Device.model
    ).order_by(
        func.count(Sale.id).desc()
    ).limit(5).all()
    
    return render_template('reports/dashboard.html',
        stats={
            'total_sales': sales_data.total_sales or 0,
            'total_revenue': float(sales_data.total_revenue or 0),
            'available_devices': inventory_data.available_devices,
            'outstanding_credit': float(credit_data.outstanding_credit or 0),
            'sales_growth': calculate_growth_rate(days)
        },
        chart_data={
            'dates': [str(row.date) for row in trend_data],
            'sales': [row.sales_count for row in trend_data]
        },
        payment_data={
            'cash_sales': next((row.count for row in payment_data if row.payment_type == 'cash'), 0),
            'credit_sales': next((row.count for row in payment_data if row.payment_type == 'credit'), 0)
        },
        recent_sales=recent_sales,
        top_products=top_products)
