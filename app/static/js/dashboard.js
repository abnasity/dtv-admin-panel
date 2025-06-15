// Initialize dashboard data
function initializeDashboardData() {
    try {
        // Validate window.dashboardData exists with required fields
        if (!window.dashboardData?.stats || !window.dashboardData?.chartData || !window.dashboardData?.paymentData) {
            console.error('Missing required dashboard data');
            return null;
        }
        
        return {
            stats: window.dashboardData.stats,
            chartData: window.dashboardData.chartData,
            paymentData: window.dashboardData.paymentData
        };
    } catch (error) {
        console.error('Error initializing dashboard data:', error);
        return null;
    }
}

// Dashboard Charts Configuration
document.addEventListener('DOMContentLoaded', function() {
    // Get initial data
    const dashData = initializeDashboardData();
    if (!dashData) {
        showAlert('danger', 'Failed to initialize dashboard data');
        return;
    }
    
    const { stats, chartData, paymentData } = dashData;
    
    // Initialize Sales Trend Chart
    const salesCtx = document.getElementById('salesChart')?.getContext('2d');
    if (!salesCtx) {
        console.error('Sales chart context not found');
        return;
    }
    
    const salesChart = new Chart(salesCtx, {
        type: 'line',
        data: {
            labels: chartData.dates || [],
            datasets: [
                {
                    label: 'Sales Count',
                    data: chartData.sales || [],
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    fill: false,
                    tension: 0.3,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    yAxisID: 'y'
                },
                {
                    label: 'Revenue',
                    data: chartData.revenue || [],
                    borderColor: '#198754',
                    backgroundColor: 'rgba(25, 135, 84, 0.1)',
                    fill: false,
                    tension: 0.3,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            if (context.dataset.label === 'Sales Count') {
                                return `Sales: ${context.parsed.y}`;
                            } else if (context.dataset.label === 'Revenue') {
                                return `Revenue: $${context.parsed.y.toLocaleString()}`;
                            }
                            return context.dataset.label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxTicksLimit: 8
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: true,
                    grid: {
                        borderDash: [2],
                        drawBorder: false
                    },
                    ticks: {
                        stepSize: 1
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: true,
                    grid: {
                        drawOnChartArea: false
                    },
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });

    // Initialize Payment Types Chart
    const paymentCtx = document.getElementById('paymentChart')?.getContext('2d');
    if (!paymentCtx) {
        console.error('Payment chart context not found');
        return;
    }
    
    const paymentChart = new Chart(paymentCtx, {
        type: 'doughnut',
        data: {
            labels: ['Cash', 'Credit'],
            datasets: [{
                data: [paymentData.cash_sales || 0, paymentData.credit_sales || 0],
                backgroundColor: ['#198754', '#ffc107']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((context.parsed / total) * 100);
                            return `${context.label}: ${context.parsed} (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '70%'
        }
    });

    // Handle date range updates
    window.updateDateRange = function(days) {
        showLoading();
        fetch(`/api/reports/summary?days=${days}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                updateDashboard(data);
                hideLoading();
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('danger', 'Failed to update dashboard data');
                hideLoading();
            });
    };

    // Update dashboard with new data
    window.updateDashboard = function(data) {
        try {
            // Update stats safely with fallbacks
            const totalSales = document.getElementById('totalSales');
            if (totalSales) {
                totalSales.textContent = data.sales_metrics?.total_sales || 0;
            }
            
            const totalRevenue = document.getElementById('totalRevenue');
            if (totalRevenue) {
                totalRevenue.textContent = formatCurrency(data.sales_metrics?.total_revenue || 0);
            }
            
            const availableDevices = document.getElementById('availableDevices');
            if (availableDevices) {
                availableDevices.textContent = data.inventory_metrics?.available_devices || 0;
            }
            
            const outstandingCredit = document.getElementById('outstandingCredit');
            if (outstandingCredit) {
                outstandingCredit.textContent = formatCurrency(data.credit_metrics?.total_outstanding || 0);
            }
            
            // Update sales trend chart if it exists
            if (salesChart) {
                salesChart.data.labels = data.sales_trend?.dates || [];
                salesChart.data.datasets[0].data = data.sales_trend?.values || [];
                salesChart.update();
            }
            
            // Update payment breakdown chart if it exists
            if (paymentChart) {
                paymentChart.data.datasets[0].data = [
                    data.payment_breakdown?.cash || 0,
                    data.payment_breakdown?.credit || 0
                ];
                paymentChart.update();
            }
        } catch (error) {
            console.error('Error updating dashboard:', error);
            showAlert('danger', 'Failed to update dashboard');
        }
    };
});
