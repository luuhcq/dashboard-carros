from django.db import migrations


def seed_initial_company(apps, schema_editor):
    Company = apps.get_model('core', 'Company')
    if not Company.objects.exists():
        Company.objects.create(name='Revenda Principal')


def remove_seeded_company(apps, schema_editor):
    Company = apps.get_model('core', 'Company')
    Company.objects.filter(name='Revenda Principal').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_initial_company, remove_seeded_company),
    ]
