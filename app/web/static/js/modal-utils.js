/**
 * Утилиты для стилизованных модальных окон (замена confirm и prompt)
 */

/**
 * Показывает стилизованное модальное окно подтверждения
 * @param {string} title - Заголовок модального окна
 * @param {string} message - Сообщение
 * @param {string} confirmText - Текст кнопки подтверждения (по умолчанию "Да")
 * @param {string} cancelText - Текст кнопки отмены (по умолчанию "Отмена")
 * @param {string} confirmClass - Класс стиля кнопки подтверждения (danger, warning, primary и т.д.)
 * @returns {Promise<boolean>} - true если подтверждено, false если отменено
 */
function showConfirmModal(title, message, confirmText = 'Да', cancelText = 'Отмена', confirmClass = 'danger') {
    return new Promise((resolve) => {
        // Создаем уникальный ID для модального окна
        const modalId = 'confirmModal_' + Date.now();
        
        // HTML структура модального окна
        const modalHTML = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header border-0 pb-0">
                            <h5 class="modal-title" id="${modalId}Label">
                                <i class="fas fa-exclamation-triangle text-warning me-2"></i>${title}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <p class="mb-0">${message}</p>
                        </div>
                        <div class="modal-footer border-0 pt-0">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                <i class="fas fa-times me-1"></i>${cancelText}
                            </button>
                            <button type="button" class="btn btn-${confirmClass}" id="${modalId}ConfirmBtn">
                                <i class="fas fa-check me-1"></i>${confirmText}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Добавляем модальное окно в DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        const modalElement = document.getElementById(modalId);
        const modal = new bootstrap.Modal(modalElement);
        const confirmBtn = document.getElementById(modalId + 'ConfirmBtn');
        
        // Обработчики событий
        confirmBtn.addEventListener('click', () => {
            modal.hide();
            resolve(true);
            // Удаляем модальное окно после закрытия
            modalElement.addEventListener('hidden.bs.modal', () => {
                modalElement.remove();
            }, { once: true });
        });
        
        modalElement.addEventListener('hidden.bs.modal', () => {
            resolve(false);
            modalElement.remove();
        }, { once: true });
        
        // Показываем модальное окно
        modal.show();
    });
}

/**
 * Показывает стилизованное модальное окно с полем ввода
 * @param {string} title - Заголовок модального окна
 * @param {string} message - Сообщение/подсказка
 * @param {string} placeholder - Placeholder для поля ввода
 * @param {string} defaultValue - Значение по умолчанию
 * @param {string} inputType - Тип поля (text, password, и т.д.)
 * @param {string} confirmText - Текст кнопки подтверждения
 * @param {string} cancelText - Текст кнопки отмены
 * @param {Function} validator - Функция валидации (опционально)
 * @returns {Promise<string|null>} - Введенное значение или null если отменено
 */
function showPromptModal(title, message, placeholder = '', defaultValue = '', inputType = 'text', 
                        confirmText = 'Подтвердить', cancelText = 'Отмена', validator = null) {
    return new Promise((resolve) => {
        const modalId = 'promptModal_' + Date.now();
        
        const modalHTML = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header border-0 pb-0">
                            <h5 class="modal-title" id="${modalId}Label">
                                <i class="fas fa-edit text-primary me-2"></i>${title}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            ${message ? `<p class="mb-3">${message}</p>` : ''}
                            <div class="mb-0">
                                <label for="${modalId}Input" class="form-label visually-hidden">Ввод</label>
                                <input type="${inputType}" 
                                       class="form-control" 
                                       id="${modalId}Input" 
                                       placeholder="${placeholder}"
                                       value="${defaultValue}"
                                       autocomplete="off">
                                <div id="${modalId}Error" class="invalid-feedback"></div>
                            </div>
                        </div>
                        <div class="modal-footer border-0 pt-0">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                <i class="fas fa-times me-1"></i>${cancelText}
                            </button>
                            <button type="button" class="btn btn-primary" id="${modalId}ConfirmBtn">
                                <i class="fas fa-check me-1"></i>${confirmText}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        const modalElement = document.getElementById(modalId);
        const modal = new bootstrap.Modal(modalElement);
        const input = document.getElementById(modalId + 'Input');
        const confirmBtn = document.getElementById(modalId + 'ConfirmBtn');
        const errorDiv = document.getElementById(modalId + 'Error');
        const formControl = input.closest('.mb-0');
        
        // Фокус на поле ввода при открытии
        modalElement.addEventListener('shown.bs.modal', () => {
            input.focus();
            input.select();
        }, { once: true });
        
        // Обработка Enter для подтверждения
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                confirmBtn.click();
            }
        });
        
        // Обработчик подтверждения
        confirmBtn.addEventListener('click', () => {
            const value = input.value.trim();
            
            // Валидация если есть
            if (validator) {
                const validationResult = validator(value);
                if (validationResult !== true) {
                    input.classList.add('is-invalid');
                    errorDiv.textContent = validationResult || 'Неверное значение';
                    return;
                }
            }
            
            modal.hide();
            resolve(value || null);
            modalElement.addEventListener('hidden.bs.modal', () => {
                modalElement.remove();
            }, { once: true });
        });
        
        // Сброс валидации при вводе
        input.addEventListener('input', () => {
            input.classList.remove('is-invalid');
            errorDiv.textContent = '';
        });
        
        modalElement.addEventListener('hidden.bs.modal', () => {
            resolve(null);
            modalElement.remove();
        }, { once: true });
        
        modal.show();
    });
}

/**
 * Показывает стилизованное модальное окно с полем ввода для подтверждения действия
 * (например, ввод "DELETE" для удаления)
 * @param {string} title - Заголовок
 * @param {string} message - Сообщение
 * @param {string} confirmValue - Требуемое значение для подтверждения
 * @param {string} placeholder - Placeholder для поля ввода
 * @param {string} confirmText - Текст кнопки подтверждения
 * @param {string} cancelText - Текст кнопки отмены
 * @returns {Promise<boolean>} - true если введено правильное значение, false иначе
 */
function showConfirmInputModal(title, message, confirmValue, placeholder = '', 
                               confirmText = 'Подтвердить', cancelText = 'Отмена') {
    return new Promise((resolve) => {
        const modalId = 'confirmInputModal_' + Date.now();
        
        const modalHTML = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content border-danger">
                        <div class="modal-header border-danger bg-danger bg-opacity-10 pb-0">
                            <h5 class="modal-title text-danger" id="${modalId}Label">
                                <i class="fas fa-exclamation-triangle me-2"></i>${title}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-warning mb-3">
                                <i class="fas fa-info-circle me-2"></i>${message}
                            </div>
                            <div class="mb-0">
                                <label for="${modalId}Input" class="form-label fw-bold">Для подтверждения введите: <code>${confirmValue}</code></label>
                                <input type="text" 
                                       class="form-control" 
                                       id="${modalId}Input" 
                                       placeholder="${placeholder || `Введите "${confirmValue}"`}"
                                       value=""
                                       autocomplete="off">
                                <div id="${modalId}Error" class="invalid-feedback"></div>
                            </div>
                        </div>
                        <div class="modal-footer border-danger bg-danger bg-opacity-10 pt-0">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                <i class="fas fa-times me-1"></i>${cancelText}
                            </button>
                            <button type="button" class="btn btn-danger" id="${modalId}ConfirmBtn" disabled>
                                <i class="fas fa-check me-1"></i>${confirmText}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        const modalElement = document.getElementById(modalId);
        const modal = new bootstrap.Modal(modalElement);
        const input = document.getElementById(modalId + 'Input');
        const confirmBtn = document.getElementById(modalId + 'ConfirmBtn');
        const errorDiv = document.getElementById(modalId + 'Error');
        
        // Фокус на поле ввода при открытии
        modalElement.addEventListener('shown.bs.modal', () => {
            input.focus();
        }, { once: true });
        
        // Проверка введенного значения
        input.addEventListener('input', () => {
            const value = input.value.trim();
            const isValid = value === confirmValue;
            
            confirmBtn.disabled = !isValid;
            
            if (value && !isValid) {
                input.classList.add('is-invalid');
                errorDiv.textContent = 'Введенное значение не совпадает';
            } else {
                input.classList.remove('is-invalid');
                errorDiv.textContent = '';
            }
        });
        
        // Обработка Enter
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !confirmBtn.disabled) {
                e.preventDefault();
                confirmBtn.click();
            }
        });
        
        // Обработчик подтверждения
        confirmBtn.addEventListener('click', () => {
            if (input.value.trim() === confirmValue) {
                modal.hide();
                resolve(true);
                modalElement.addEventListener('hidden.bs.modal', () => {
                    modalElement.remove();
                }, { once: true });
            }
        });
        
        modalElement.addEventListener('hidden.bs.modal', () => {
            resolve(false);
            modalElement.remove();
        }, { once: true });
        
        modal.show();
    });
}


