// Get CSRF token from meta tag
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Helper function for making fetch requests with CSRF token
async function fetchWithCsrf(url, options = {}) {
    // Ensure options.headers exists
    options.headers = options.headers || {};
    
    // Add CSRF token to headers
    options.headers['X-CSRFToken'] = getCsrfToken();
    
    // Make the fetch request
    const response = await fetch(url, options);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response;
}

function toggleUserStatus(userId, action) {
    fetchWithCsrf(`/auth/users/${userId}/toggle_status`, {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert(data.error || 'Failed to update user status');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to update user status');
    });
}

async function editUser(userId) {
    try {
        const response = await fetchWithCsrf(`/auth/users/${userId}/edit`);
        const user = await response.json();
        
        // Clear previous error messages
        clearEditFormErrors();
        
        // Fill the edit form with user data
        document.getElementById('edit_user_id').value = user.id;
        document.getElementById('edit_username').value = user.username;
        document.getElementById('edit_email').value = user.email;
        document.getElementById('edit_role').value = user.role;
        document.getElementById('edit_password').value = ''; // Clear password field

        // Show the modal
        const editModal = new bootstrap.Modal(document.getElementById('editUserModal'));
        editModal.show();
    } catch (error) {
        console.error('Error:', error);
        showAlert('danger', 'Failed to load user data: ' + error.message);
    }
}

// Handle edit form submission
document.getElementById('editUserForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Clear previous error messages
    clearEditFormErrors();
    
    const userId = document.getElementById('edit_user_id').value;
    const formData = {
        username: document.getElementById('edit_username').value,
        email: document.getElementById('edit_email').value,
        role: document.getElementById('edit_role').value,
        password: document.getElementById('edit_password').value
    };
    
    try {
        const response = await fetchWithCsrf(`/auth/users/${userId}/edit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('editUserModal')).hide();
            showAlert('success', result.message);
            // Reload page after short delay to show the alert
            setTimeout(() => location.reload(), 1500);
        } else {
            showAlert('danger', result.error);
            if (result.errors) {
                displayFormErrors(result.errors);
            }
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('danger', 'Failed to update user');
    }
});

function clearEditFormErrors() {
    document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    document.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
}

function displayFormErrors(errors) {
    Object.entries(errors).forEach(([field, message]) => {
        const input = document.getElementById(`edit_${field}`);
        if (input) {
            input.classList.add('is-invalid');
            const feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            feedback.textContent = message;
            input.parentNode.appendChild(feedback);
        }
    });
}

// Handle bulk selections
document.addEventListener('DOMContentLoaded', function() {
    const selectAllCheckbox = document.getElementById('selectAllUsers');
    const userCheckboxes = document.querySelectorAll('.user-select');
    const bulkActionsBtn = document.getElementById('bulkActionsBtn');
    const bulkActionsDropdown = document.getElementById('bulkActionsDropdown');
    const selectedCountBadge = document.querySelector('.selected-count');

    selectAllCheckbox?.addEventListener('change', function() {
        userCheckboxes.forEach(checkbox => {
            if (!checkbox.disabled) {
                checkbox.checked = this.checked;
            }
        });
        updateBulkActionsVisibility();
    });

    userCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateBulkActionsVisibility);
    });

    function updateBulkActionsVisibility() {
        const selectedCount = document.querySelectorAll('.user-select:checked').length;
        bulkActionsBtn.disabled = selectedCount === 0;
        bulkActionsDropdown.style.display = selectedCount > 0 ? 'block' : 'none';
        selectedCountBadge.textContent = selectedCount;
    }
});

// Bulk actions
async function bulkActivate() {
    await bulkUpdateStatus(true);
}

async function bulkDeactivate() {
    await bulkUpdateStatus(false);
}

async function bulkUpdateStatus(activate) {
    const selectedUserIds = Array.from(document.querySelectorAll('.user-select:checked'))
        .map(checkbox => checkbox.value);

    if (!selectedUserIds.length) return;

    try {
        const response = await fetchWithCsrf('/auth/users/bulk_status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_ids: selectedUserIds,
                activate: activate
            })
        });

        const data = await response.json();
        if (data.success) {
            location.reload();
        } else {
            alert(data.error || 'Failed to update users');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to update users');
    }
}

// Password strength meter
function checkPasswordStrength(password) {
    let strength = 0;
    const feedback = [];

    // Length check
    if (password.length < 8) {
        feedback.push('Password should be at least 8 characters long');
    } else {
        strength += 1;
    }

    // Contains number
    if (/\d/.test(password)) {
        strength += 1;
    } else {
        feedback.push('Add numbers');
    }

    // Contains lowercase
    if (/[a-z]/.test(password)) {
        strength += 1;
    } else {
        feedback.push('Add lowercase letters');
    }

    // Contains uppercase
    if (/[A-Z]/.test(password)) {
        strength += 1;
    } else {
        feedback.push('Add uppercase letters');
    }

    // Contains special char
    if (/[^A-Za-z0-9]/.test(password)) {
        strength += 1;
    } else {
        feedback.push('Add special characters');
    }

    return {
        score: strength,
        feedback: feedback.join(', ')
    };
}

// Add password strength meter to password fields
document.addEventListener('DOMContentLoaded', function() {
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(input => {
        const meterContainer = document.createElement('div');
        meterContainer.className = 'password-strength-meter mt-2';
        meterContainer.innerHTML = `
            <div class="progress" style="height: 5px;">
                <div class="progress-bar" role="progressbar" style="width: 0%"></div>
            </div>
            <small class="form-text text-muted feedback-text"></small>
        `;
        input.parentNode.insertBefore(meterContainer, input.nextSibling);

        input.addEventListener('input', function() {
            const strength = checkPasswordStrength(this.value);
            const progressBar = meterContainer.querySelector('.progress-bar');
            const feedbackText = meterContainer.querySelector('.feedback-text');

            // Update progress bar
            progressBar.style.width = `${(strength.score / 5) * 100}%`;
            progressBar.className = 'progress-bar';
            if (strength.score <= 2) {
                progressBar.classList.add('bg-danger');
            } else if (strength.score <= 3) {
                progressBar.classList.add('bg-warning');
            } else {
                progressBar.classList.add('bg-success');
            }

            // Update feedback text
            feedbackText.textContent = strength.feedback || 'Strong password';
        });
    });
});

// Function to handle edit user form submission
async function handleEditUser(userId) {
    // Clear previous errors
    document.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
    document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    
    // Get user data
    try {
        const response = await fetch(`/users/${userId}/edit`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) throw new Error('Failed to fetch user data');
        
        const userData = await response.json();
        
        // Populate form
        document.getElementById('edit_username').value = userData.username;
        document.getElementById('edit_email').value = userData.email;
        document.getElementById('edit_role').value = userData.role;
        document.getElementById('edit_user_id').value = userId;
        
        // Show modal
        const editModal = new bootstrap.Modal(document.getElementById('editUserModal'));
        editModal.show();
        
    } catch (error) {
        showAlert('error', 'Failed to load user data');
    }
}

// Handle form submission
document.getElementById('editUserForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const userId = document.getElementById('edit_user_id').value;
    const formData = new FormData(this);
    
    try {
        const response = await fetch(`/users/${userId}/edit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify(Object.fromEntries(formData))
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Close modal and refresh page
            bootstrap.Modal.getInstance(document.getElementById('editUserModal')).hide();
            showAlert('success', 'User updated successfully');
            setTimeout(() => location.reload(), 1500);
        } else {
            // Display error message
            showAlert('error', result.error);
            
            // Highlight invalid fields if specified
            if (result.errors) {
                Object.entries(result.errors).forEach(([field, message]) => {
                    const input = document.getElementById(`edit_${field}`);
                    if (input) {
                        input.classList.add('is-invalid');
                        const feedback = document.createElement('div');
                        feedback.className = 'invalid-feedback';
                        feedback.textContent = message;
                        input.parentNode.appendChild(feedback);
                    }
                });
            }
        }
    } catch (error) {
        showAlert('error', 'An error occurred while updating the user');
    }
});

// Helper function to show alerts
function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => alertDiv.remove(), 5000);
}
