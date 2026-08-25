from django.db import migrations

CREATE_SEQUENCE = "CREATE SEQUENCE vehicle_internal_code_seq START WITH 1 INCREMENT BY 1;"
DROP_SEQUENCE = "DROP SEQUENCE vehicle_internal_code_seq;"


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0002_alter_vehicle_brand_alter_vehicle_model'),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_SEQUENCE, reverse_sql=DROP_SEQUENCE),
    ]
