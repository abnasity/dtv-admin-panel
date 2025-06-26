
// CSRF token
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

async function fetchWithCsrf(url, options = {}) {
    options.headers = options.headers || {};
    options.headers['X-CSRFToken'] = getCsrfToken();

    const response = await fetch(url, options);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return response;
}

// Edit User Modal logic
async function editUser(userId) {
    try {
        const response = await fetchWithCsrf(`/auth/users/${userId}/edit`);
        const user = await response.json();

        clearEditFormErrors();

        // Populate fields
        document.getElementById('edit_user_id').value = user.id;
        document.getElementById('edit_username').value = user.username;
        document.getElementById('edit_email').value = user.email;
        document.getElementById('edit_role').value = user.role;
        document.getElementById('edit_password').value = '';

        const addressSelect = document.getElementById('edit_address');
        const newAddressInput = document.getElementById('edit_new_address');
        const newAddressField = document.getElementById('editNewAddressField');

        if (addressSelect && newAddressInput && newAddressField) {
            const foundOption = [...addressSelect.options].find(opt => opt.value === user.address);

            if (foundOption) {
                addressSelect.value = user.address;
                newAddressInput.value = '';
                newAddressField.style.display = 'none';
            } else {
                addressSelect.value = '__new__';
                newAddressInput.value = user.address || '';
                newAddressField.style.display = 'block';
            }
        }

        // Show modal
        const editModal = new bootstrap.Modal(document.getElementById('editUserModal'));
        editModal.show();

    } catch (error) {
        console.error('Error loading user:', error);
        showAlert('danger', 'Failed to load user data.');
    }
}

// Handle form submission
document.getElementById('editUserForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    clearEditFormErrors();

    const userId = document.getElementById('edit_user_id').value;
    const addressSelect = document.getElementById('edit_address');
    const newAddressInput = document.getElementById('edit_new_address');

    const address = (addressSelect && addressSelect.value === '__new__')
        ? (newAddressInput ? newAddressInput.value : '')
        : (addressSelect ? addressSelect.value : '');

    const formData = {
        username: document.getElementById('edit_username').value,
        email: document.getElementById('edit_email').value,
        role: document.getElementById('edit_role').value,
        password: document.getElementById('edit_password').value,
        address: address
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
            bootstrap.Modal.getInstance(document.getElementById('editUserModal')).hide();
            showAlert('success', result.message || 'User updated successfully');
            setTimeout(() => location.reload(), 1500);
        } else {
            showAlert('danger', result.error || 'Something went wrong');
            if (result.errors) {
                displayFormErrors(result.errors);
            }
        }
    } catch (error) {
        console.error('Submit error:', error);
        showAlert('danger', 'Failed to update user.');
    }
});

// Toggle new address input visibility when user changes dropdown
document.addEventListener('DOMContentLoaded', function () {
    const addressSelect = document.getElementById('edit_address');
    const newAddressField = document.getElementById('editNewAddressField');

    if (addressSelect && newAddressField) {
        addressSelect.addEventListener('change', () => {
            newAddressField.style.display = addressSelect.value === '__new__' ? 'block' : 'none';
        });
    }
});

// Helpers
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

// ADD USER JS
document.addEventListener('DOMContentLoaded', function () {
    const roleSelect = document.querySelector('#addUserModal select[name="role"]');
    const addressSelect = document.querySelector('#addUserModal select[name="address"]');
    const newAddressField = document.querySelector('#addUserModal #newAddressField');

    function toggleNewAddressField() {
        if (addressSelect.value === '__new__') {
            newAddressField.style.display = 'block';
        } else {
            newAddressField.style.display = 'none';
            const input = newAddressField.querySelector('input[name="new_address"]');
            if (input) input.value = '';
        }
    }

    // Only apply if elements exist
    if (roleSelect && addressSelect && newAddressField) {
        // Initial state
        toggleNewAddressField();

        // Watch for changes
        addressSelect.addEventListener('change', toggleNewAddressField);
    }
});



function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show mt-3`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    const container = document.querySelector('.container') || document.body;
    container.prepend(alertDiv);
    setTimeout(() => alertDiv.remove(), 5000);
}

