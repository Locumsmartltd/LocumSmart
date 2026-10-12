// Toast notifications. Server messages are rendered into #toastStack by base.html;
// scripts can add their own with window.rsToast(message, type).
(function () {
    var stack = document.getElementById('toastStack');
    if (!stack) return;

    var AUTO_DISMISS_MS = 6000;

    function dismiss(toast) {
        if (!toast.parentNode) return;
        toast.classList.add('rs-toast-hide');
        setTimeout(function () { toast.remove(); }, 250);
    }

    function arm(toast) {
        var closeButton = toast.querySelector('.rs-toast-close');
        if (closeButton) closeButton.addEventListener('click', function () { dismiss(toast); });

        // Errors and sticky notices stay until closed so they cannot be missed
        if (toast.classList.contains('rs-toast-error') || toast.classList.contains('rs-toast-sticky')) return;

        var timer = setTimeout(function () { dismiss(toast); }, AUTO_DISMISS_MS);
        toast.addEventListener('mouseenter', function () { clearTimeout(timer); });
        toast.addEventListener('mouseleave', function () {
            timer = setTimeout(function () { dismiss(toast); }, AUTO_DISMISS_MS);
        });
    }

    window.rsToast = function (message, type) {
        type = type || 'info';
        var toast = document.createElement('div');
        toast.className = 'rs-toast rs-toast-' + type;
        toast.setAttribute('role', type === 'error' ? 'alert' : 'status');

        var text = document.createElement('span');
        text.className = 'rs-toast-text';
        text.textContent = message;

        var closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'rs-toast-close';
        closeButton.setAttribute('aria-label', 'Dismiss');
        closeButton.innerHTML = '&times;';

        toast.appendChild(text);
        toast.appendChild(closeButton);
        stack.appendChild(toast);
        arm(toast);
        return toast;
    };
    window.rsToast.dismiss = dismiss;

    Array.prototype.forEach.call(stack.querySelectorAll('.rs-toast'), arm);
})();
