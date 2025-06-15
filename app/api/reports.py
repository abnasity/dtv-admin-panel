from flask import Blueprint, request, jsonify
from flask_login import login_required
from sqlalchemy import func
from app.models import Sale, Device, User
from app import db
from app.decorators import admin_required
from datetime import datetime, timedelta

bp = Blueprint('reports', __name__)

@bp.route('/reports/summary', methods=['GET'])
@login_required
@admin_required
def get_summary():
    """Get summary of sales and inventory"""
    # Get date range from query parameters
    days = int(request.args.get('days', 30))
    date_from = datetime.utcnow() - timedelta(days=days)
    
    # Total sales amount and profit
    sales_data = db.session.query(
        func.count(Sale.id).label('total_sales'),
        func.sum(Sale.sale_price).label('total_revenue'),
        func.sum(Sale.sale_price - Device.purchase_price).label('total_profit')
    ).join(Device).filter(Sale.sale_date >= date_from).first()
    
    # Inventory status
    inventory_data = db.session.query(
        func.count(Device.id).label('total_devices'),
        func.count(Device.id).filter(Device.status == 'available').label('available_devices'),
        func.count(Device.id).filter(Device.status == 'sold').label('sold_devices')
    ).first()
    
    # Outstanding credit amount
    credit_data = db.session.query(
        func.sum(Sale.sale_price - Sale.amount_paid).label('total_credit')
    ).filter(Sale.payment_type == 'credit').first()
    
    return jsonify({
        'period_days': days,
        'sales_metrics': {
            'total_sales': sales_data.total_sales or 0,
            'total_revenue': float(sales_data.total_revenue or 0),
            'total_profit': float(sales_data.total_profit or 0)
        },
        'inventory_metrics': {
            'total_devices': inventory_data.total_devices,
            'available_devices': inventory_data.available_devices,
            'sold_devices': inventory_data.sold_devices
        },
        'credit_metrics': {
            'total_outstanding': float(credit_data.total_credit or 0)
        }
    })

@bp.route('/reports/staff/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_staff_performance(user_id):
    """Get performance metrics for specific staff member"""
    user = User.query.get_or_404(user_id)
    
    # Get date range from query parameters
    days = int(request.args.get('days', 30))
    date_from = datetime.utcnow() - timedelta(days=days)
    
    # Staff sales performance
    sales_data = db.session.query(
        func.count(Sale.id).label('total_sales'),
        func.sum(Sale.sale_price).label('total_revenue'),
        func.sum(Sale.sale_price - Device.purchase_price).label('total_profit'),
        func.avg(Sale.sale_price - Device.purchase_price).label('avg_profit_per_sale')
    ).join(Device).filter(
        Sale.seller_id == user_id,
        Sale.sale_date >= date_from
    ).first()
    
    # Payment type breakdown
    payment_data = db.session.query(
        Sale.payment_type,
        func.count(Sale.id).label('count'),
        func.sum(Sale.sale_price).label('total')
    ).filter(
        Sale.seller_id == user_id,
        Sale.sale_date >= date_from
    ).group_by(Sale.payment_type).all()
    
    return jsonify({
        'user': user.to_dict(),
        'period_days': days,
        'performance_metrics': {
            'total_sales': sales_data.total_sales or 0,
            'total_revenue': float(sales_data.total_revenue or 0),
            'total_profit': float(sales_data.total_profit or 0),
            'avg_profit_per_sale': float(sales_data.avg_profit_per_sale or 0)
        },
        'payment_breakdown': [{
            'type': data.payment_type,
            'count': data.count,
            'total': float(data.total or 0)
        } for data in payment_data]
    })

@bp.route('/reports/inventory', methods=['GET'])
@login_required
@admin_required
def get_inventory_report():
    """Get detailed inventory report with brand/model breakdown"""
    # Inventory by brand and model
    inventory_data = db.session.query(
        Device.brand,
        Device.model,
        func.count(Device.id).label('total'),
        func.count(Device.id).filter(Device.status == 'available').label('available'),
        func.count(Device.id).filter(Device.status == 'sold').label('sold'),
        func.avg(Device.purchase_price).label('avg_purchase_price'),
        func.avg(Sale.sale_price).label('avg_sale_price')
    ).outerjoin(Sale).group_by(Device.brand, Device.model).all()
    
    return jsonify([{
        'brand': data.brand,
        'model': data.model,
        'total': data.total,
        'available': data.available,
        'sold': data.sold,
        'avg_purchase_price': float(data.avg_purchase_price or 0),
        'avg_sale_price': float(data.avg_sale_price or 0),
        'avg_profit_margin': float((data.avg_sale_price or 0) - (data.avg_purchase_price or 0))
    } for data in inventory_data])

@bp.route('/reports/trends', methods=['GET'])
@login_required
@admin_required
def get_sales_trends():
    """Get daily/monthly sales trends"""
    # Get date range from query parameters
    days = int(request.args.get('days', 30))
    group_by = request.args.get('group', 'day')  # 'day' or 'month'
    date_from = datetime.utcnow() - timedelta(days=days)
    
    if group_by == 'month':
        # Monthly sales trends
        sales_trend = db.session.query(
            func.date_trunc('month', Sale.sale_date).label('date'),
            func.count(Sale.id).label('sales_count'),
            func.sum(Sale.sale_price).label('revenue'),
            func.sum(Sale.sale_price - Device.purchase_price).label('profit')
        )
    else:
        # Daily sales trends
        sales_trend = db.session.query(
            func.date_trunc('day', Sale.sale_date).label('date'),
            func.count(Sale.id).label('sales_count'),
            func.sum(Sale.sale_price).label('revenue'),
            func.sum(Sale.sale_price - Device.purchase_price).label('profit')
        )
    
    sales_trend = sales_trend.join(Device).filter(
        Sale.sale_date >= date_from
    ).group_by('date').order_by('date').all()
    
    return jsonify([{
        'date': data.date.isoformat(),
        'sales_count': data.sales_count,
        'revenue': float(data.revenue or 0),
        'profit': float(data.profit or 0)
    } for data in sales_trend])