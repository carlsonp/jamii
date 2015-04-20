# forms.py
from django import forms

class CodeImpactFilter(forms.Form):
    limit = forms.IntegerField(required=True)
    epochtime = forms.IntegerField(required=True)
    relativetoemail = forms.CharField(required=False)
