// Barcode Scanner functionality
let isScanning = false;
let scannerModal = null;
let currentTargetInput = null;

// Initialize scanner when page loads
document.addEventListener('DOMContentLoaded', function() {
    scannerModal = new bootstrap.Modal(document.getElementById('scannerModal'));
    
    // Handle modal events
    const scannerModalEl = document.getElementById('scannerModal');
    scannerModalEl.addEventListener('shown.bs.modal', function() {
        startScanning();
    });
    
    scannerModalEl.addEventListener('hidden.bs.modal', function() {
        stopScanner();
    });
});

function startScanner(targetInputId) {
    currentTargetInput = targetInputId;
    scannerModal.show();
}

function startScanning() {
    if (!isScanning) {
        initializeScanner();
    }
}

function initializeScanner() {
    Quagga.init({
        inputStream: {
            name: "Live",
            type: "LiveStream",
            target: document.querySelector("#interactive"),
            constraints: {
                width: 640,
                height: 480,
                facingMode: "environment"
            },
        },
        locate: true,
        numOfWorkers: navigator.hardwareConcurrency || 4,
        decoder: {
            readers: [
                "ean_13_reader",
                "ean_8_reader",
                "code_128_reader",
                "code_39_reader",
                "upc_reader"
            ],
            debug: {
                drawBoundingBox: true,
                showFrequency: true,
                drawScanline: true,
                showPattern: true
            },
            multiple: false
        }
    }, function(err) {
        if (err) {
            console.error("Failed to initialize scanner:", err);
            alert("Failed to start scanner. Please check camera permissions.");
            return;
        }
        console.log("Scanner initialized successfully");
        isScanning = true;
        Quagga.start();
    });

    // Handle scanned codes
    Quagga.onDetected(function(result) {
        if (result.codeResult.code) {
            let code = result.codeResult.code;
            // Filter IMEI to ensure it's 15 digits
            code = code.replace(/[^0-9]/g, '');
            if (code.length === 15) {
                const targetInput = document.getElementById(currentTargetInput);
                targetInput.value = code;
                // Dispatch a custom event that pages can listen for
                targetInput.dispatchEvent(new CustomEvent('barcodeScanned', {
                    detail: { code: code }
                }));
                stopScanner();
                scannerModal.hide();
            }
        }
    });
}

function stopScanner() {
    if (isScanning) {
        Quagga.stop();
        isScanning = false;
    }
}
