// ===== CSRF Helpers =====
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

// ===== Edit User Logic =====
async function editUser(userId) {
    try {
        const response = await fetchWithCsrf(`/users/${userId}/edit`);
        const user = await response.json();

        clearFormErrors('edit');

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
        new bootstrap.Modal(document.getElementById('editUserModal')).show();

    } catch (error) {
        console.error('Error loading user:', error);
        showAlert('danger', 'Failed to load user data.');
    }
}

// ===== Edit User Submit =====
document.getElementById('editUserForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    clearFormErrors('edit');

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
        const response = await fetchWithCsrf(`/users/${userId}/edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (result.success) {
            bootstrap.Modal.getInstance(document.getElementById('editUserModal')).hide();
            showAlert('success', result.message || 'User updated successfully');
            setTimeout(() => location.reload(), 1500);
        } else {
            showAlert('danger', result.error || 'Something went wrong');
            if (result.errors) displayFormErrors(result.errors, 'edit');
        }
    } catch (error) {
        console.error('Submit error:', error);
        showAlert('danger', 'Failed to update user.');
    }
});

// ===== Add User Submit =====
document.getElementById('addUserForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const formData = new FormData(this);

    try {
        const response = await fetch('/users/create', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            console.error("Add user error:", data);
            alert(`Error: ${data.message}`);
            return;
        }

        alert(data.message);
        // Optionally reload or update the users list
        window.location.reload();

    } catch (error) {
        console.error("Add user error:", error);
        alert("Unexpected error. Check console for details.");
    }
});

// ===== Address Toggle Logic =====
document.addEventListener('DOMContentLoaded', function () {
    function setupAddressToggle(modalId, selectId, fieldId) {
        const addressSelect = document.getElementById(selectId);
        const newAddressField = document.getElementById(fieldId);

        if (addressSelect && newAddressField) {
            const toggle = () => {
                newAddressField.style.display = addressSelect.value === '__new__' ? 'block' : 'none';
            };
            toggle();
            addressSelect.addEventListener('change', toggle);
        }
    }

    setupAddressToggle('editUserModal', 'edit_address', 'editNewAddressField');
    setupAddressToggle('addUserModal', 'add_address', 'newAddressField');

    // Attach edit button click events
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', () => editUser(btn.dataset.userId));
    });
});

// ===== Helpers =====
function clearFormErrors(prefix) {
    document.querySelectorAll(`#${prefix}UserForm .is-invalid`).forEach(el => el.classList.remove('is-invalid'));
    document.querySelectorAll(`#${prefix}UserForm .invalid-feedback`).forEach(el => el.remove());
}

function displayFormErrors(errors, prefix) {
    Object.entries(errors).forEach(([field, message]) => {
        const input = document.getElementById(`${prefix}_${field}`);
        if (input) {
            input.classList.add('is-invalid');
            const feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            feedback.textContent = message;
            input.parentNode.appendChild(feedback);
        }
    });
}

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