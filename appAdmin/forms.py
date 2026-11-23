from django import forms

from .models import BookingConfirmationTerms, Employer


class CandidateInvoiceRecipientForm(forms.ModelForm):
    class Meta:
        model = Employer
        fields = (
            'candidate_invoice_company',
            'candidate_invoice_contact',
            'candidate_invoice_email',
            'candidate_invoice_address',
        )

    def clean(self):
        cleaned = super().clean()
        # Blank fields deliberately mean "use the employer account details".
        for name in self.Meta.fields:
            value = cleaned.get(name)
            if isinstance(value, str):
                cleaned[name] = value.strip()
        return cleaned


class BookingConfirmationTermsForm(forms.ModelForm):
    class Meta:
        model = BookingConfirmationTerms
        fields = ('pharmacy_candidate_terms', 'primary_care_candidate_terms')
        widgets = {
            'pharmacy_candidate_terms': forms.Textarea(attrs={'rows': 12}),
            'primary_care_candidate_terms': forms.Textarea(attrs={'rows': 12}),
        }

    def clean(self):
        cleaned = super().clean()
        for name in self.Meta.fields:
            value = (cleaned.get(name) or '').strip()
            if not value:
                self.add_error(name, 'Terms cannot be blank.')
            cleaned[name] = value
        return cleaned
