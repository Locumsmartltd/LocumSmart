// Modal dialog overlay.
//   window.rsModal({ type: 'success' | 'error', title, message, items: [], buttonText, onClose })
// base.html also uses it to show the "Registered Successfully" confirmation.
(function () {
    var ICONS = { success: '&#10003;', error: '!' };

    window.rsModal = function (options) {
        var type = options.type === 'success' ? 'success' : 'error';
        var previousFocus = document.activeElement;

        var overlay = document.createElement('div');
        overlay.className = 'rs-modal-overlay';

        var dialog = document.createElement('div');
        dialog.className = 'rs-modal rs-modal-' + type;
        dialog.setAttribute('role', type === 'error' ? 'alertdialog' : 'dialog');
        dialog.setAttribute('aria-modal', 'true');
        dialog.setAttribute('aria-labelledby', 'rsModalTitle');

        var icon = document.createElement('div');
        icon.className = 'rs-modal-icon';
        icon.setAttribute('aria-hidden', 'true');
        icon.innerHTML = ICONS[type];
        dialog.appendChild(icon);

        var title = document.createElement('h2');
        title.id = 'rsModalTitle';
        title.textContent = options.title || '';
        dialog.appendChild(title);

        if (options.message) {
            var message = document.createElement('p');
            message.textContent = options.message;
            dialog.appendChild(message);
        }

        if (options.items && options.items.length) {
            var list = document.createElement('ul');
            options.items.forEach(function (text) {
                var item = document.createElement('li');
                item.textContent = text;
                list.appendChild(item);
            });
            dialog.appendChild(list);
        }

        var button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-primary';
        button.textContent = options.buttonText || 'OK';
        dialog.appendChild(button);

        function close() {
            document.removeEventListener('keydown', onKeydown);
            overlay.remove();
            document.body.style.overflow = '';
            if (options.onClose) {
                options.onClose();
            } else if (previousFocus && previousFocus.focus) {
                previousFocus.focus();
            }
        }

        function onKeydown(event) {
            if (event.key === 'Escape') close();
            // The dialog has a single control, so keep focus on it
            if (event.key === 'Tab') { event.preventDefault(); button.focus(); }
        }

        button.addEventListener('click', close);
        overlay.addEventListener('click', function (event) { if (event.target === overlay) close(); });
        document.addEventListener('keydown', onKeydown);

        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden';
        button.focus();
    };

    // Server messages tagged 'modal', handed over by base.html
    var serverMessage = document.querySelector('.rs-modal-message');
    if (serverMessage) {
        window.rsModal({
            type: serverMessage.getAttribute('data-type') === 'success' ? 'success' : 'error',
            title: serverMessage.getAttribute('data-title'),
            message: serverMessage.getAttribute('data-message'),
            buttonText: 'Try again'
        });
    }

    // Registration success, handed over by base.html
    var registered = document.getElementById('registrationSuccess');
    if (registered) {
        window.rsModal({
            type: 'success',
            title: 'Registered Successfully',
            message: registered.getAttribute('data-message'),
            buttonText: 'Continue',
            onClose: function () { window.location.href = registered.getAttribute('data-redirect'); }
        });
    }
})();
