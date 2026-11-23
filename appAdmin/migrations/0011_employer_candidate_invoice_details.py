from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('appAdmin', '0010_search_column_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='employer',
            name='candidate_invoice_address',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='employer',
            name='candidate_invoice_company',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='employer',
            name='candidate_invoice_contact',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='employer',
            name='candidate_invoice_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
