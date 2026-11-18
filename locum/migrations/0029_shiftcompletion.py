from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('appAdmin', '0010_search_column_indexes'),
        ('locum', '0028_search_column_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShiftCompletion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shift_date', models.DateField(db_index=True)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('break_minutes', models.PositiveIntegerField(default=0)),
                ('candidate_note', models.CharField(blank=True, max_length=500)),
                ('status', models.CharField(choices=[('pending', 'Pending review'), ('approved', 'Approved'), ('declined', 'Declined')], db_index=True, default='pending', max_length=20)),
                ('admin_note', models.CharField(blank=True, max_length=500)),
                ('reported_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shift_completions', to='locum.job')),
                ('locum', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shift_completions', to='locum.locum')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_shift_completions', to='appAdmin.admin')),
            ],
            options={'ordering': ['shift_date', 'id']},
        ),
        migrations.AddConstraint(
            model_name='shiftcompletion',
            constraint=models.UniqueConstraint(fields=('job', 'locum', 'shift_date'), name='unique_shift_completion'),
        ),
    ]
