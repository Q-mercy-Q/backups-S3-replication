const usersTable = document.getElementById('usersTable');
const refreshBtn = document.getElementById('refreshUsers');
const newUserForm = document.getElementById('newUserForm');

async function fetchJSON(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        },
        ...options
    });
    
    let data;
    try {
        data = await response.json();
    } catch (e) {
        throw new Error(`Server returned invalid JSON: ${response.status} ${response.statusText}`);
    }
    
    if (!response.ok || data.status === 'error') {
        const errorMsg = data.message || data.error || `Request failed with status ${response.status}`;
        throw new Error(errorMsg);
    }
    return data;
}

function renderUsers(users = []) {
    if (!users.length) {
        usersTable.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">No users found</td></tr>';
        return;
    }
    usersTable.innerHTML = users.map(user => `
        <tr data-user-id="${user.id}">
            <td>${user.username}</td>
            <td>${user.email || '-'}</td>
            <td>${user.is_admin ? '<span class="badge bg-primary">Admin</span>' : '<span class="badge bg-secondary">User</span>'}</td>
            <td>
                <span class="badge ${user.is_active ? 'bg-success' : 'bg-danger'}">
                    ${user.is_active ? 'Active' : 'Disabled'}
                </span>
            </td>
            <td>${user.created_at ? new Date(user.created_at).toLocaleString() : '-'}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-secondary toggle-active">${user.is_active ? 'Disable' : 'Enable'}</button>
                    <button class="btn btn-outline-secondary toggle-role">${user.is_admin ? 'Make User' : 'Make Admin'}</button>
                    <button class="btn btn-outline-primary change-password" title="Изменить пароль">
                        <i class="fas fa-key"></i>
                    </button>
                    <button class="btn btn-outline-danger delete-user" title="Удалить пользователя">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

async function loadUsers() {
    try {
        const { users } = await fetchJSON('/api/admin/users');
        renderUsers(users);
    } catch (error) {
        console.error(error);
        alert('Failed to load users: ' + error.message);
    }
}

async function updateUser(userId, payload) {
    const { user } = await fetchJSON(`/api/admin/users/${userId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload)
    });
    return user;
}

usersTable?.addEventListener('click', async (event) => {
    const button = event.target.closest('button');
    if (!button) return;
    const row = button.closest('tr');
    const userId = row.dataset.userId;
    const isToggleActive = button.classList.contains('toggle-active');
    const isToggleRole = button.classList.contains('toggle-role');
    const isChangePassword = button.classList.contains('change-password') || button.closest('.change-password');
    const isDeleteUser = button.classList.contains('delete-user') || button.closest('.delete-user');

    if (!userId) return;

    // Обработка смены пароля
    if (isChangePassword) {
        const username = row.querySelector('td:first-child').textContent;
        const modal = new bootstrap.Modal(document.getElementById('changePasswordModal'));
        document.getElementById('changePasswordUserId').value = userId;
        document.querySelector('#changePasswordModalLabel').innerHTML = `
            <i class="fas fa-key me-2"></i>Изменить пароль для: <strong>${username}</strong>
        `;
        document.getElementById('changePasswordForm').reset();
        document.getElementById('passwordError').classList.add('d-none');
        modal.show();
        return;
    }

    // Обработка удаления пользователя
    if (isDeleteUser) {
        const username = row.querySelector('td:first-child').textContent;
        const isAdmin = row.querySelector('.badge.bg-primary') !== null;
        const modal = new bootstrap.Modal(document.getElementById('deleteUserModal'));
        document.getElementById('deleteUserId').value = userId;
        document.querySelector('#deleteUserModalLabel').textContent = `Удалить пользователя: ${username}`;
        document.querySelector('#deleteUserInfo').innerHTML = `
            <p>Вы уверены, что хотите удалить пользователя <strong>${username}</strong>?</p>
            ${isAdmin ? '<p class="text-warning"><i class="fas fa-exclamation-triangle me-1"></i>Это администратор.</p>' : ''}
            <p class="text-danger mb-0"><strong>Это действие нельзя отменить!</strong> Все данные пользователя, включая его конфигурацию, будут удалены.</p>
        `;
        modal.show();
        return;
    }

    const originalText = button.innerHTML;
    try {
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        if (isToggleActive) {
            const activeBadge = row.querySelector('.badge.bg-success, .badge.bg-danger');
            const currentlyActive = activeBadge?.classList.contains('bg-success') || false;
            await updateUser(userId, { is_active: !currentlyActive });
        } else if (isToggleRole) {
            const roleBadge = row.querySelector('.badge.bg-primary, .badge.bg-secondary');
            const currentlyAdmin = roleBadge?.classList.contains('bg-primary') || false;
            await updateUser(userId, { is_admin: !currentlyAdmin });
        }
        await loadUsers();
    } catch (error) {
        alert('Failed to update user: ' + error.message);
    } finally {
        button.disabled = false;
        // После перезагрузки таблицы кнопки будут пересозданы, поэтому просто включаем кнопку
        if (button.parentElement) {
            button.innerHTML = originalText;
        }
    }
});

newUserForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const submitBtn = newUserForm.querySelector('button[type="submit"]');
    const originalText = submitBtn?.innerHTML;
    
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
    }
    
    try {
        const formData = new FormData(newUserForm);
        const payload = {
            username: formData.get('username')?.trim() || '',
            email: formData.get('email')?.trim() || null,
            password: formData.get('password') || '',
            is_admin: formData.get('is_admin') === 'on'
        };
        
        if (!payload.username || !payload.password) {
            throw new Error('Username and password are required');
        }
        
        if (payload.password.length < 8) {
            throw new Error('Password must be at least 8 characters long');
        }
        
        await fetchJSON('/api/admin/users', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        
        newUserForm.reset();
        const collapse = bootstrap.Collapse.getInstance(document.getElementById('createUserForm'));
        collapse?.hide();
        await loadUsers();
        
        // Показываем уведомление об успехе
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success alert-dismissible fade show';
        alertDiv.innerHTML = `
            <i class="fas fa-check-circle me-1"></i>User created successfully
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
        setTimeout(() => alertDiv.remove(), 5000);
        
    } catch (error) {
        const errorMsg = error.message || 'Failed to create user';
        alert('Error: ' + errorMsg);
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText || '<i class="fas fa-save me-1"></i>Save User';
        }
    }
});

refreshBtn?.addEventListener('click', () => loadUsers());

// Обработка формы смены пароля
const changePasswordForm = document.getElementById('changePasswordForm');
const savePasswordBtn = document.getElementById('savePasswordBtn');
const passwordError = document.getElementById('passwordError');

savePasswordBtn?.addEventListener('click', async () => {
    const userId = document.getElementById('changePasswordUserId').value;
    const newPassword = document.getElementById('newPasswordInput').value;
    const confirmPassword = document.getElementById('confirmPasswordInput').value;

    // Валидация
    passwordError.classList.add('d-none');
    
    if (!newPassword || !confirmPassword) {
        passwordError.textContent = 'Пожалуйста, заполните все поля';
        passwordError.classList.remove('d-none');
        return;
    }

    if (newPassword.length < 8) {
        passwordError.textContent = 'Пароль должен содержать минимум 8 символов';
        passwordError.classList.remove('d-none');
        return;
    }

    if (newPassword !== confirmPassword) {
        passwordError.textContent = 'Пароли не совпадают';
        passwordError.classList.remove('d-none');
        return;
    }

    const originalText = savePasswordBtn.innerHTML;
    try {
        savePasswordBtn.disabled = true;
        savePasswordBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Сохранение...';
        
        await updateUser(parseInt(userId), { password: newPassword });
        
        // Закрываем модальное окно
        const modal = bootstrap.Modal.getInstance(document.getElementById('changePasswordModal'));
        modal.hide();
        
        // Показываем уведомление об успехе
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success alert-dismissible fade show';
        alertDiv.innerHTML = `
            <i class="fas fa-check-circle me-1"></i>Пароль успешно изменен
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
        setTimeout(() => alertDiv.remove(), 5000);
        
    } catch (error) {
        passwordError.textContent = error.message || 'Ошибка при изменении пароля';
        passwordError.classList.remove('d-none');
    } finally {
        savePasswordBtn.disabled = false;
        savePasswordBtn.innerHTML = originalText;
    }
});

// Обработка Enter в полях пароля
document.getElementById('newPasswordInput')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        savePasswordBtn?.click();
    }
});

document.getElementById('confirmPasswordInput')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        savePasswordBtn?.click();
    }
});

// Сброс формы при закрытии модального окна
document.getElementById('changePasswordModal')?.addEventListener('hidden.bs.modal', () => {
    changePasswordForm?.reset();
    passwordError.classList.add('d-none');
});

// Обработка удаления пользователя
const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

confirmDeleteBtn?.addEventListener('click', async () => {
    const userId = document.getElementById('deleteUserId').value;
    
    if (!userId) {
        alert('Ошибка: ID пользователя не найден');
        return;
    }

    const originalText = confirmDeleteBtn.innerHTML;
    try {
        confirmDeleteBtn.disabled = true;
        confirmDeleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Удаление...';
        
        const data = await fetchJSON(`/api/admin/users/${userId}`, {
            method: 'DELETE'
        });
        
        // Закрываем модальное окно
        const modal = bootstrap.Modal.getInstance(document.getElementById('deleteUserModal'));
        modal.hide();
        
        // Обновляем список пользователей
        await loadUsers();
        
        // Показываем уведомление об успехе
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success alert-dismissible fade show';
        alertDiv.innerHTML = `
            <i class="fas fa-check-circle me-1"></i>Пользователь успешно удален
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
        setTimeout(() => alertDiv.remove(), 5000);
        
    } catch (error) {
        alert('Ошибка при удалении пользователя: ' + error.message);
    } finally {
        confirmDeleteBtn.disabled = false;
        confirmDeleteBtn.innerHTML = originalText;
    }
});

document.addEventListener('DOMContentLoaded', () => {
    loadUsers();
});


