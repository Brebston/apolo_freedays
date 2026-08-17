from django import forms
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm

from .models import User


class UserCreationForm(DjangoUserCreationForm):
    """
    User creation form in the Django Admin.

    - The `username` field is missing from the form; it is generated automatically in `User.save()`
      (based on `email` or `telegram_id`, or a random string if both are empty).
    - The password is optional: it is required only for coordinators/administrators who
      need to log in to the Django Admin itself. If left blank, the user
      is assigned an "unusable" password (making Django Admin login
      impossible), though this does not affect access to the bot in any way.
    """

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        required=False,
        help_text="Leave blank if this is a regular employee without access to the Django Admin.",
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
        required=False,
    )

    class Meta(DjangoUserCreationForm.Meta):
        model = User

    def save(self, commit=True):
        user = forms.ModelForm.save(self, commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        if commit:
            user.save()
        return user
