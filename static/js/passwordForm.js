// Password rules for the set / reset password page. Problems are reported in a
// pop-up dialog (modal.js) rather than inline text.
// Keep the rules in sync with PASSWORD_RULES in structure/passwords.py
(function () {
    var form = document.getElementById('passwordForm');
    if (!form || !window.rsModal) return;

    var RULES = [
        [function (p) { return p.length >= 8; }, 'At least 8 characters'],
        [function (p) { return /[a-z]/.test(p); }, 'A lowercase letter'],
        [function (p) { return /[A-Z]/.test(p); }, 'An uppercase letter'],
        [function (p) { return /\d/.test(p); }, 'A number'],
        [function (p) { return /[^A-Za-z0-9]/.test(p); }, 'A special character (for example ! @ # ?)']
    ];

    var passwordField = form.querySelector('[name="password"]');
    var confirmField = form.querySelector('[name="confirm-password"]');

    function showProblems(items) {
        var mismatch = items.length === 1 && items[0] === 'Both password fields must match';
        window.rsModal({
            type: 'error',
            title: mismatch ? 'Passwords do not match' : 'Password format is not valid',
            message: mismatch ? 'Please enter the same password in both fields.' : 'Your password is still missing:',
            items: mismatch ? [] : items,
            buttonText: 'Try again',
            onClose: function () { (mismatch ? confirmField : passwordField).focus(); }
        });
    }

    form.addEventListener('submit', function (event) {
        var password = passwordField.value;
        var problems = RULES.filter(function (rule) { return !rule[0](password); })
                            .map(function (rule) { return rule[1]; });
        if (!problems.length && password !== confirmField.value) {
            problems = ['Both password fields must match'];
        }
        if (problems.length) {
            event.preventDefault();
            showProblems(problems);
        }
    });

    // Problems found by the server (only reached if the check above was bypassed)
    var serverProblems = document.getElementById('passwordProblems');
    if (serverProblems) showProblems(JSON.parse(serverProblems.textContent));
})();
