import re

from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

SITE_URL = 'https://locumsmart.co.uk'

# (check, requirement shown to the user). Keep in sync with static/js/passwordForm.js
PASSWORD_RULES = [
    (lambda p: len(p) >= 8, 'At least 8 characters'),
    (lambda p: re.search(r'[a-z]', p), 'A lowercase letter'),
    (lambda p: re.search(r'[A-Z]', p), 'An uppercase letter'),
    (lambda p: re.search(r'\d', p), 'A number'),
    (lambda p: re.search(r'[^A-Za-z0-9]', p), 'A special character (for example ! @ # ?)'),
]


def password_problems(password):
    # Requirements the given password does not meet (empty list = acceptable)
    password = password or ''
    return [label for check, label in PASSWORD_RULES if not check(password)]


def password_setup_url(user):
    # Single-use link that lets this user choose a password. It stops working once
    # the password changes, or after settings.PASSWORD_RESET_TIMEOUT.
    path = reverse('forgot_password', kwargs={
        'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
    })
    return SITE_URL + path
