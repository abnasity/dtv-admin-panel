// Sales page functionality
let previousIMEI = '';

// Initialize functionality when page loads
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
});

function setupEventListeners() {
    // Listen for barcode scan events
    const imeiInput = document.getElementById('imei');
    imeiInput.addEventListener('barcodeScanned', function(e) {
        findDevice();
    });

    // Set up payment field validation
    const salePriceField = document.getElementById('sale_price');
    if (salePriceField) {
        salePriceField.addEventListener('change', function() {
            updateAmountPaid();
            togglePaymentFields();
        });
    }

    // Set up payment type change handler
    const paymentTypeField = document.getElementById('payment_type');
    if (paymentTypeField) {
        paymentTypeField.addEventListener('change', togglePaymentFields);
    }
}

async function findDevice() {
    const imei = document.getElementById('imei').value;
    if (!imei || imei === previousIMEI) return;
    
    previousIMEI = imei;
    
    // Validate IMEI format
    if (!/^\d{15}$/.test(imei)) {
        showAlert('Invalid IMEI format. Must be 15 digits.', 'danger');
        resetForm();
        return;
    }

    try {
        const response = await fetch(`/api/devices/${imei}`);
        const data = await response.json();
        
        if (data.success) {
            displayDeviceDetails(data.device);
            updateAmountPaid();
        } else {
            showAlert('Device not found or already sold', 'danger');
            resetForm();
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('Error finding device', 'danger');
        resetForm();
    }
}

function displayDeviceDetails(device) {
    document.getElementById('deviceBrand').textContent = device.brand;
    document.getElementById('deviceModel').textContent = device.model;
    document.getElementById('devicePurchasePrice').textContent = device.purchase_price;
    document.getElementById('deviceDetails').style.display = 'block';
}

function resetForm() {
    document.getElementById('saleForm').reset();
    document.getElementById('deviceDetails').style.display = 'none';
    previousIMEI = '';
}

function updateAmountPaid() {
    const paymentType = document.getElementById('payment_type').value;
    const salePrice = document.getElementById('sale_price').value;
    const amountPaidField = document.getElementById('amount_paid');
    
    if (paymentType === 'cash') {
        amountPaidField.value = salePrice;
    }
}

function togglePaymentFields() {
    const paymentType = document.getElementById('payment_type').value;
    const amountPaidField = document.getElementById('amount_paid');
    const salePriceField = document.getElementById('sale_price');
    
    if (paymentType === 'cash') {
        amountPaidField.value = salePriceField.value;
        amountPaidField.readOnly = true;
    } else {
        amountPaidField.readOnly = false;
        amountPaidField.min = '0';
        amountPaidField.max = salePriceField.value;
    }
}

function showAlert(message, type) {
    const existingAlert = document.querySelector('.alert');
    if (existingAlert) {
        existingAlert.remove();
    }

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show mt-3`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Insert alert before the form
    const form = document.getElementById('saleForm');
    form.parentNode.insertBefore(alertDiv, form);

    // Auto dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}
