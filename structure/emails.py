import re
from html import unescape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from structure.passwords import SITE_URL, password_setup_url

LOGO_URL = SITE_URL + '/static/images/logo.JPG'


def render_branded_email(template, context=None):
    # (html, plain text) for templates/emails/<template>.html
    html = render_to_string(f'emails/{template}.html', {
        'site_url': SITE_URL,
        'logo_url': LOGO_URL,
        **(context or {}),
    })
    return html, html_to_text(html)


def html_to_text(html):
    # Plain-text fallback for mail clients that do not show HTML
    def link(match):
        # Keep link targets, which strip_tags would otherwise drop (image-only links have no label)
        label = strip_tags(match.group(2)).strip()
        return f'{label}: {match.group(1)}' if label else ''

    text = re.sub(r'<a\s[^>]*href="(?!mailto:)([^"]+)"[^>]*>(.*?)</a>', link, html, flags=re.S)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = unescape(strip_tags(text))
    text = '\n'.join(line.strip() for line in text.splitlines())
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def send_branded_email(template, subject, to, context=None, cc=None, fail_silently=False):
    # Send templates/emails/<template>.html in the shared branded layout
    html, text = render_branded_email(template, context)
    message = EmailMultiAlternatives(subject, text, settings.EMAIL_HOST_USER, to, cc=cc)
    message.attach_alternative(html, 'text/html')
    return message.send(fail_silently=fail_silently)


def send_approval_email(locum):
    # "Registration approved / welcome" email, with the link to set a password
    send_branded_email(
        'locum_approved',
        'LocumSmart Ltd: Your LocumSmart Account Has Been Approved',
        [locum.Email],
        {
            'locum': locum,
            'password_url': password_setup_url(locum),
            'details': [('Email', locum.Email), ('Locum Type', locum.user_type)],
        })
