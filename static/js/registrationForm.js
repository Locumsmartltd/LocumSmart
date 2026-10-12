// Field-level validation for the locum registration / profile forms.
// Replaces the browser's own validation bubbles with a notification box
// shown directly above each field that needs attention.
(function () {
    var form = document.querySelector('form[data-validate-fields]');
    if (!form) return;

    function fieldLabel(field) {
        var wrapper = field.closest('.field');
        var label = wrapper && wrapper.querySelector('label');
        if (!label) return 'This field';
        var clone = label.cloneNode(true);
        clone.querySelectorAll('.req, .hint').forEach(function (el) { el.remove(); });
        return clone.textContent.replace(/\s+/g, ' ').trim() || 'This field';
    }

    function messageFor(field) {
        var validity = field.validity;
        var label = fieldLabel(field);
        if (validity.valueMissing) {
            if (field.type === 'checkbox') return 'Please accept the terms and conditions to continue.';
            if (field.type === 'file') return 'Please upload this document.';
            if (field.tagName === 'SELECT') return 'Please select an option.';
            return label + ' is required.';
        }
        if (validity.typeMismatch && field.type === 'email') return 'Please enter a valid email address.';
        if (validity.badInput && field.type === 'date') return 'Please enter a complete, valid date.';
        return field.validationMessage || (label + ' is not valid.');
    }

    // The box sits right above the control; the terms checkbox lives inside
    // its own label, so there the box goes above the whole label.
    function anchorFor(field) {
        return field.closest('.terms-label') || field;
    }

    function errorBoxFor(field) {
        var previous = anchorFor(field).previousElementSibling;
        return previous && previous.classList.contains('field-error') ? previous : null;
    }

    function clearError(field) {
        var box = errorBoxFor(field);
        if (box) box.remove();
        field.removeAttribute('aria-invalid');
        field.removeAttribute('aria-describedby');
    }

    function showError(field) {
        var box = errorBoxFor(field);
        if (!box) {
            box = document.createElement('div');
            box.className = 'field-error';
            box.setAttribute('role', 'alert');
            box.id = 'error-' + field.name;
            var anchor = anchorFor(field);
            anchor.parentNode.insertBefore(box, anchor);
        }
        box.textContent = messageFor(field);
        field.setAttribute('aria-invalid', 'true');
        field.setAttribute('aria-describedby', box.id);
    }

    function isInvalid(field) {
        return field.name && field.willValidate && !field.validity.valid;
    }

    var summaryToast = null;

    form.addEventListener('submit', function (event) {
        var firstInvalid = null;
        var invalidCount = 0;
        Array.prototype.forEach.call(form.elements, function (field) {
            if (isInvalid(field)) {
                showError(field);
                invalidCount += 1;
                if (!firstInvalid) firstInvalid = field;
            } else if (field.name) {
                clearError(field);
            }
        });
        if (window.rsToast && summaryToast) window.rsToast.dismiss(summaryToast);
        if (firstInvalid) {
            event.preventDefault();
            if (window.rsToast) {
                summaryToast = window.rsToast(
                    invalidCount === 1
                        ? 'Please correct the highlighted field before submitting.'
                        : 'Please correct the ' + invalidCount + ' highlighted fields before submitting.',
                    'error');
            }
            (errorBoxFor(firstInvalid) || firstInvalid).scrollIntoView({ behavior: 'smooth', block: 'center' });
            firstInvalid.focus({ preventScroll: true });
        }
    });

    // Once a field has been flagged, re-check it as the applicant corrects it.
    function recheck(event) {
        var field = event.target;
        if (!field.name || !errorBoxFor(field)) return;
        if (isInvalid(field)) {
            showError(field);
        } else {
            clearError(field);
        }
    }
    form.addEventListener('input', recheck);
    form.addEventListener('change', recheck);
})();
