# mall_settings/forms.py
from django import forms
from .models import SiteSetting
from ckeditor.widgets import CKEditorWidget

class SiteSettingForm(forms.ModelForm):
    class Meta:
        model = SiteSetting
        fields = '__all__'
        widgets = {
            'site_name': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'business_hours': forms.TextInput(attrs={'class': 'form-control'}),
            'ceo_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_number': forms.TextInput(attrs={'class': 'form-control'}),
            'commerce_number': forms.TextInput(attrs={'class': 'form-control'}),
            'business_address': forms.TextInput(attrs={'class': 'form-control'}),
            'business_license_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'footer_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'terms_of_service': CKEditorWidget(),
            'privacy_policy': CKEditorWidget(),
            'ecommerce_notice': CKEditorWidget(),
            'return_policy': CKEditorWidget(),
        }