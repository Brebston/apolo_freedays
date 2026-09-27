from django.db import migrations, models

STATUS_CHOICES = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("cancelled", "Cancelled"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_sickleavedocument_fix_broadcast_recurrence"),
    ]

    operations = [
        migrations.AlterField(
            model_name="absencerequest",
            name="status",
            field=models.CharField(choices=STATUS_CHOICES, default="pending", max_length=10, verbose_name="Status"),
        ),
        migrations.AlterField(
            model_name="servicerequest",
            name="status",
            field=models.CharField(choices=STATUS_CHOICES, default="pending", max_length=10, verbose_name="Status"),
        ),
        migrations.AddField(
            model_name="absencerequest",
            name="cancelled_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Cancelled by worker"),
        ),
        migrations.AddField(
            model_name="absencerequest",
            name="sick_note_reminders_sent",
            field=models.PositiveSmallIntegerField(default=0, verbose_name="Sick note reminders sent"),
        ),
        migrations.AddField(
            model_name="absencerequest",
            name="sick_note_last_reminded_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Last sick note reminder"),
        ),
        migrations.AddField(
            model_name="servicerequest",
            name="cancelled_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Cancelled by worker"),
        ),
    ]
