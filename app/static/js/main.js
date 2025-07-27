// Format currency values
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-NG', {
        style: 'currency',
        currency: 'NGN'
    }).format(amount);
}

// Format dates
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-NG', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Mobile Navigation Toggle
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.getElementById('nav-toggle');
    const navItems = document.querySelector('.nav-items');
    
    if (navToggle && navItems) {
        navToggle.addEventListener('click', function() {
            navItems.classList.toggle('show');
        });

        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            if (!navToggle.contains(event.target) && !navItems.contains(event.target)) {
                navItems.classList.remove('show');
            }
        });
    }

    // Payment method selection
    const paymentOptions = document.querySelectorAll('.payment-option');
    if (paymentOptions.length > 0) {
        paymentOptions.forEach(option => {
            option.addEventListener('click', function() {
                document.querySelectorAll('.payment-option').forEach(opt => {
                    opt.classList.remove('active');
                });
                this.classList.add('active');
                
                // Update amount paid field based on selection
                const paymentType = this.getAttribute('data-payment');
                const amountPaid = document.getElementById('amount-paid');
                const salePrice = document.getElementById('sale-price');
                
                if (amountPaid && salePrice) {
                    if (paymentType === 'credit') {
                        amountPaid.value = (parseFloat(salePrice.value) / 2).toFixed(2); // 50% of sale price
                        amountPaid.placeholder = 'Enter deposit amount';
                    } else {
                        amountPaid.value = salePrice.value; // Full sale price
                    }
                }
            });
        });
    }
});

// Show/hide loading spinner
function showLoading() {
    document.getElementById('loading-spinner')?.classList.remove('d-none');
}

function hideLoading() {
    document.getElementById('loading-spinner')?.classList.add('d-none');
}

// Handle API errors
function handleApiError(error) {
    let message = 'An error occurred. Please try again.';
    if (error.response) {
        message = error.response.data.error || message;
    }
    showAlert('danger', message);
}

// Show alert message
function showAlert(type, message) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    const alertContainer = document.querySelector('.alert-container') || document.createElement('div');
    alertContainer.classList.add('alert-container');
    alertContainer.innerHTML = alertHtml;
    
    if (!document.body.contains(alertContainer)) {
        document.querySelector('main').insertAdjacentElement('afterbegin', alertContainer);
    }
}

// Confirm action
function confirmAction(message) {
    return new Promise((resolve) => {
        if (window.confirm(message)) {
            resolve(true);
        } else {
            resolve(false);
        }
    });
}

// IMEI validation
function validateIMEI(imei) {
    const regex = /^\d{15}$/;
    return regex.test(imei);
}

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        new bootstrap.Tooltip(tooltip);
    });
});

// Handle form validation
function validateForm(form) {
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        return false;
    }
    return true;
}

// Debounce function for search inputs
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(
        () => showAlert('success', 'Copied to clipboard!'),
        () => showAlert('danger', 'Failed to copy to clipboard')
    );
}

// Export data to CSV
function exportToCSV(data, filename) {
    const csvContent = "data:text/csv;charset=utf-8," + data.map(row => 
        Object.values(row).map(val => `"${val}"`).join(",")
    ).join("\n");
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${filename}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
