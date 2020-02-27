from django import forms
from .models import Tracker


class CheckForm(forms.ModelForm):

    class Meta:
        model = Tracker
        fields = ('name', 'weight')

        # 要想使用bootstrap的格式，用下面的东西
        widgets = {
            'name': forms.Select(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control'})
        }
