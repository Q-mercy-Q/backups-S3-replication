const emailForm = document.getElementById('emailForm');
const passwordForm = document.getElementById('passwordForm');
const alertContainer = document.getElementById('alertContainer');

function showAlert(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), 5000);
}

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

emailForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const submitBtn = emailForm.querySelector('button[type="submit"]');
    const originalText = submitBtn?.innerHTML;
    const emailInput = document.getElementById('emailInput');
    
    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Сохранение...';
        
        const email = emailInput.value.trim() || null;
        
        const { user } = await fetchJSON('/api/auth/profile', {
            method: 'PATCH',
            body: JSON.stringify({ email })
        });
        
        document.getElementById('emailDisplay').textContent = user.email || 'не указан';
        emailInput.value = user.email || '';
        
        showAlert('<i class="fas fa-check-circle me-1"></i>Email успешно обновлен', 'success');
    } catch (error) {
        showAlert(`<i class="fas fa-exclamation-circle me-1"></i>Ошибка: ${error.message}`, 'danger');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
});

passwordForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const submitBtn = passwordForm.querySelector('button[type="submit"]');
    const originalText = submitBtn?.innerHTML;
    
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    // Валидация
    if (newPassword.length < 8) {
        showAlert('<i class="fas fa-exclamation-circle me-1"></i>Новый пароль должен содержать минимум 8 символов', 'danger');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showAlert('<i class="fas fa-exclamation-circle me-1"></i>Пароли не совпадают', 'danger');
        return;
    }
    
    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Изменение...';
        
        await fetchJSON('/api/auth/profile', {
            method: 'PATCH',
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });
        
        // Очищаем форму
        passwordForm.reset();
        
        showAlert('<i class="fas fa-check-circle me-1"></i>Пароль успешно изменен', 'success');
    } catch (error) {
        showAlert(`<i class="fas fa-exclamation-circle me-1"></i>Ошибка: ${error.message}`, 'danger');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
});




