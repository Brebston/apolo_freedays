from django.db import migrations, models
import django.db.models.deletion

# У 0008 значення «одноразової» розсилки випадково стало рядком з типографськими
# лапками. Розсилки, створені до 0008, мають значення "none" і після неї перестали
# розпізнаватись як одноразові. Нормалізуємо обидва варіанти до "none".
BROKEN_NONE = "none\u201d, \u201cNone (one-time)"


def normalize_recurrence(apps, schema_editor):
    Broadcast = apps.get_model("core", "Broadcast")
    Broadcast.objects.filter(recurrence=BROKEN_NONE).update(recurrence="none")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_servicerequest_departmentresponsibleperson"),
    ]

    operations = [
        migrations.RunPython(normalize_recurrence, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="broadcast",
            name="recurrence",
            field=models.CharField(
                choices=[
                    ("none", "None (one-time)"),
                    ("daily", "Daily"),
                    ("weekly", "Weekly"),
                    ("monthly", "Monthly"),
                ],
                default="none",
                max_length=23,
                verbose_name="Repetition",
            ),
        ),
        migrations.CreateModel(
            name="SickLeaveDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "filename",
                    models.CharField(max_length=255, verbose_name="File name"),
                ),
                (
                    "content_type",
                    models.CharField(max_length=100, verbose_name="Content type"),
                ),
                ("size", models.PositiveIntegerField(verbose_name="Size (bytes)")),
                ("content", models.BinaryField(blank=True, editable=False, null=True)),
                (
                    "uploaded_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Uploaded"),
                ),
                (
                    "emailed_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Emailed"),
                ),
                (
                    "purged_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="File removed"
                    ),
                ),
                (
                    "request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="core.absencerequest",
                        verbose_name="Request",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sick leave document",
                "verbose_name_plural": "Sick leave documents",
                "ordering": ["uploaded_at"],
            },
        ),
    ]
