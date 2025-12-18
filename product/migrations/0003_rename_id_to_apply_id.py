from django.db import migrations


def rename_id_to_apply_id(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    cursor.execute("PRAGMA table_info(product_productapplication)")
    columns = [row[1] for row in cursor.fetchall()]
    if "id" in columns:
        cursor.execute("ALTER TABLE product_productapplication RENAME COLUMN id TO apply_id;")


def rename_apply_id_to_id(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    cursor.execute("PRAGMA table_info(product_productapplication)")
    columns = [row[1] for row in cursor.fetchall()]
    if "apply_id" in columns:
        cursor.execute("ALTER TABLE product_productapplication RENAME COLUMN apply_id TO id;")


class Migration(migrations.Migration):

    dependencies = [
        ("product", "0002_productapplication"),
    ]

    operations = [
        migrations.RunPython(rename_id_to_apply_id, rename_apply_id_to_id),
    ]
