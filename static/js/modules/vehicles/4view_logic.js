document.addEventListener('DOMContentLoaded', function () {
    const configEl = document.getElementById('vehicle-config');

    if (configEl) {
        try {
            window.vehicleConfig = JSON.parse(configEl.textContent);
        } catch (error) {
            window.vehicleConfig = {};
        }
    } else {
        window.vehicleConfig = window.vehicleConfig || {};
    }

    const colorBadge = document.querySelector('.vehicle-color-badge');
    if (colorBadge && window.vehicleConfig.color) {
        colorBadge.style.backgroundColor = window.vehicleConfig.color;
        if (window.vehicleConfig.colorText) {
            colorBadge.style.color = window.vehicleConfig.colorText;
        }
    }

    const selectAllCheckbox = document.getElementById('select-all');
    const handoverCheckboxes = document.querySelectorAll('.handover-checkbox');
    const deleteSelectedBtn = document.getElementById('delete-selected-btn');

    if (selectAllCheckbox && handoverCheckboxes.length > 0 && deleteSelectedBtn) {
        function updateDeleteButton() {
            const checkedCount = document.querySelectorAll('.handover-checkbox:checked').length;
            deleteSelectedBtn.disabled = checkedCount === 0;

            if (checkedCount > 0) {
                deleteSelectedBtn.innerHTML = `<i class="fas fa-trash-alt ms-1"></i> حذف المحدد (${checkedCount})`;
            } else {
                deleteSelectedBtn.innerHTML = `<i class="fas fa-trash-alt ms-1"></i> حذف المحدد`;
            }
        }

        selectAllCheckbox.addEventListener('change', function () {
            handoverCheckboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateDeleteButton();
        });

        handoverCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function () {
                const allChecked = document.querySelectorAll('.handover-checkbox:checked').length === handoverCheckboxes.length;
                selectAllCheckbox.checked = allChecked;
                updateDeleteButton();
            });
        });

        updateDeleteButton();
    }

    const confirmForms = document.querySelectorAll('.js-confirm-submit');
    confirmForms.forEach(form => {
        form.addEventListener('submit', event => {
            const message = form.getAttribute('data-confirm-message');
            if (message && !confirm(message)) {
                event.preventDefault();
            }
        });
    });
});
