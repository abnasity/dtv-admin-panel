from flask import render_template, jsonify, request, redirect, flash, url_for
from flask_login import login_required, current_user
from app.utils.decorators import admin_required
from app.models import Sale, Device, Expense
from app.forms import ExpenseForm
from app.routes.reports import bp
from app import db
from sqlalchemy import func, extract
from datetime import datetime, timedelta, date


@bp.route('/reports/dashboard')
@login_required
def dashboard():
    # Get time ranges for comparison
    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)
    previous_thirty_days = thirty_days_ago - timedelta(days=30)
    
    # Current period stats
    current_sales = Sale.query.filter(Sale.sale_date >= thirty_days_ago).count()
    current_revenue = db.session.query(
        func.sum(Sale.sale_price)
    ).filter(Sale.sale_date >= thirty_days_ago).scalar() or 0
    
    # Previous period stats for growth calculation
    previous_sales = Sale.query.filter(
        Sale.sale_date >= previous_thirty_days,
        Sale.sale_date < thirty_days_ago
    ).count()
    previous_revenue = db.session.query(
        func.sum(Sale.sale_price)
    ).filter(
        Sale.sale_date >= previous_thirty_days,
        Sale.sale_date < thirty_days_ago
    ).scalar() or 0
    
    # Calculate growth percentages
    sales_growth = ((current_sales - previous_sales) / previous_sales * 100) if previous_sales > 0 else 0
    revenue_growth = ((current_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0
    
    # Get basic stats
    stats = {
        'total_sales': current_sales,
        'total_revenue': current_revenue,
        'sales_growth': round(sales_growth, 1),
        'revenue_growth': round(revenue_growth, 1),
        'available_devices': Device.query.filter_by(status='available').count(),
        'outstanding_credit': db.session.query(
            func.sum(Sale.sale_price - Sale.amount_paid)
        ).filter(Sale.is_fully_paid == False).scalar() or 0
    }
    
    # Get sales data for chart
    sales_data = db.session.query(
        func.date(Sale.sale_date).label('date'),
        func.count(Sale.id).label('count'),
        func.sum(Sale.sale_price).label('revenue')
    ).filter(
        Sale.sale_date >= thirty_days_ago
    ).group_by(
        func.date(Sale.sale_date)
    ).order_by(func.date(Sale.sale_date)).all()
    
    # Fill in missing dates with zero values
    date_dict = {
        (thirty_days_ago + timedelta(days=i)).date(): {'count': 0, 'revenue': 0.0}
        for i in range(31)
    }
    
    for row in sales_data:
        date_dict[row.date] = {'count': row.count, 'revenue': float(row.revenue or 0)}
    
    # --- FIXED: properly indented helper and chart logic ---
    def safe_parse_date(d):
        if isinstance(d, date):
            return d
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            return None

    parsed_dates = [safe_parse_date(d) for d in date_dict.keys()]
    parsed_dates = [d for d in parsed_dates if d]

    chart_data = {
        'dates': [d.strftime("%Y-%m-%d") for d in sorted(parsed_dates)],
        'sales': [data['count'] for data in date_dict.values()],
        'revenue': [data['revenue'] for data in date_dict.values()]
    }

    # Payment type breakdown
    payment_data = {
        'cash_sales': Sale.query.filter_by(payment_type='cash').count(),
        'credit_sales': Sale.query.filter_by(payment_type='credit').count()
    }
    
    # Recent sales
    recent_sales = Sale.query.order_by(Sale.sale_date.desc()).limit(5).all()
    
    # Top products
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
    
    return render_template(
        'reports/dashboard.html',
        stats=stats,
        chart_data=chart_data,
        payment_data=payment_data,
        recent_sales=recent_sales,
        top_products=top_products
    )


@bp.route('/reports/summary')
@login_required
@admin_required
def summary():
    days = request.args.get('days', 30, type=int)
    cutoff_date = datetime.now() - timedelta(days=days)
    
    total_sales = Sale.query.filter(Sale.sale_date >= cutoff_date).count()
    total_revenue = db.session.query(
        func.sum(Sale.sale_price)
    ).filter(Sale.sale_date >= cutoff_date).scalar() or 0
    
    prev_cutoff = cutoff_date - timedelta(days=days)
    prev_sales = Sale.query.filter(
        Sale.sale_date.between(prev_cutoff, cutoff_date)
    ).count()
    prev_revenue = db.session.query(
        func.sum(Sale.sale_price)
    ).filter(Sale.sale_date.between(prev_cutoff, cutoff_date)).scalar() or 0
    
    sales_growth = ((total_sales - prev_sales) / prev_sales * 100) if prev_sales > 0 else 0
    revenue_growth = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
    
    sales_metrics = {
        'total_sales': total_sales,
        'sales_growth': round(sales_growth, 1),
        'total_revenue': round(total_revenue, 2),
        'revenue_growth': round(revenue_growth, 1)
    }
    
    inventory_metrics = {
        'available_devices': Device.query.filter_by(status='available').count()
    }
    
    credit_metrics = {
        'total_outstanding': round(db.session.query(
            func.sum(Sale.sale_price - Sale.amount_paid)
        ).scalar() or 0, 2)
    }
    
    return render_template(
        'reports/reports_summary.html',
        days=days,
        sales_metrics=sales_metrics,
        inventory_metrics=inventory_metrics,
        credit_metrics=credit_metrics
    )


@bp.route('/reports/expenses', methods=['GET', 'POST'])
@login_required
def manage_expenses():
    form = ExpenseForm()
    today = date.today() 
    if form.validate_on_submit():
        expense = Expense(
            category=form.category.data,
            description=form.description.data,
            amount=form.amount.data,
            recorded_by=current_user.id
        )
        db.session.add(expense)
        db.session.commit()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('reports.manage_expenses'))

    # Today's expenses
    today_expenses = Expense.query.filter_by(date=date.today()).all()
    total_today = sum(e.amount for e in today_expenses)

    # Current month expenses
    today = date.today()
    monthly_expenses = Expense.query.filter(
        extract('year', Expense.date) == today.year,
        extract('month', Expense.date) == today.month
    ).all()
    total_month = sum(e.amount for e in monthly_expenses)

    return render_template(
        'reports/expenses.html',
        form=form,
        expenses=today_expenses,
        total_today=total_today,
        monthly_expenses=monthly_expenses,
        total_month=total_month,
        today=today
    )