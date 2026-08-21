from django import forms


class EmojiTextarea(forms.Textarea):
    """
    A textarea with a clickable emoji bar above the field (in Django Admin).
    Does not depend on external libraries—all JS/CSS is loaded
    via Media and is located in core/static/core/admin/.
    """

    class Media:
        css = {"all": ("core/admin/emoji_picker.css",)}
        js = ("core/admin/emoji_picker.js",)

    def __init__(self, attrs=None):
        default_attrs = {"rows": 6, "class": "emoji-textarea vLargeTextField"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
