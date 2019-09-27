# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import vakt

from django import forms
from django.forms import widgets
from django.contrib import admin
from djangovakt.models import Policy
from vakt import rules
from vakt.rules.base import Rule

def get_all_rules_options():
    all_rules = []
    for name, cls in rules.__dict__.items():
        if callable(cls) and issubclass(cls, Rule):
            all_rules.append((name.lower(), name))

    return all_rules

def get_all_effects():
    return [
        ('allow', str(vakt.ALLOW_ACCESS)),
        ('deny', str(vakt.DENY_ACCESS)),
    ]

# Register your models here.
class PolicyForm(forms.ModelForm):
    actions = forms.ChoiceField(widget=widgets.SelectMultiple)
    resources = forms.ChoiceField(widget=widgets.SelectMultiple)
    subjects = forms.ChoiceField(widget=widgets.SelectMultiple)
    context = forms.ChoiceField(widget=widgets.SelectMultiple)
    effects = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['actions'].choices = get_all_rules_options()
        self.fields['resources'].choices = get_all_rules_options()
        self.fields['subjects'].choices = get_all_rules_options()
        self.fields['context'].choices = get_all_rules_options()
        self.fields['effects'].choices = get_all_effects()

        # if edit, select the propper rules in the combo

    def save(self, commit=True):
        pass

    class Meta:
        model = Policy
        fields = []

@admin.register(Policy)
class PolicyForm(admin.ModelAdmin):
    form = PolicyForm
