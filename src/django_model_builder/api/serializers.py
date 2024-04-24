from django.db import models, connection
from rest_framework import serializers
from uuid import uuid4
from api.models import FieldType, DynamicModelTable, App, Field
import types
from django.db.utils import DataError


def create_serializer_for_model(dj_model):
    """
    Given a Django model, construct a ModelSerializer for it.
    """
    name = f"{dj_model.__name__}Serializer"
    result = type(name, (serializers.ModelSerializer,), {
       "Meta": type("Meta", () ,{
           "model": dj_model,
           "fields": "__all__"
       }),
       "many": True,
    })
    return result


class DynamicModelSerializer(serializers.Serializer):
    # Dynamic model fields with the available value choices being FieldType choices
    fields = serializers.DictField(child=serializers.ChoiceField(required=True, choices=FieldType))
    
    def create(self, validated_data):
        # create a UUID which will serve as the model name
        model_id = str(uuid4())
        fields_data = validated_data.get('fields', {}).items()
        model = self.register_model(model_id, fields_data)
        return {"model_id": model_id}
    
    def register_model(self, model_id, model_fields):
        # construct a DynamicModelTable object to keep a reference to the model
        model = DynamicModelTable.objects.create(model_id=model_id, app=App.objects.first())
        # Construct the corresponding Django model and save it in the DB if necessary
        django_model = model.get_django_model()
        with connection.schema_editor() as schema_editor:
            # create and save the model fields
            for field_name, field_type in model_fields:
                # Field objects
                field = Field.objects.create(model=model, name=field_name, field_type=field_type)
                # Corresponding DB fields
                django_field_for_db = field.get_django_field()
                django_field_for_db.column = field_name
                schema_editor.add_field(django_model, django_field_for_db)
        return model
    
    def update_model(self, model_id):
        try:
            model_to_be_updated = DynamicModelTable.objects.get(model_id=model_id)
        except DynamicModelTable.DoesNotExist:
            return {"error": f"Could not find model with ID of {model_id}."}
        
        current_model_fields = model_to_be_updated.fields
        fields_data = self.validated_data.get('fields', {}).items()

        with connection.schema_editor() as schema_editor:
            # TODO add error handling for edge cases (existing field data, incompatible field change)
            django_model = model_to_be_updated.get_django_model()
            for name, field in fields_data:
                if (name,) in current_model_fields.values_list("name"):
                    updated_field = current_model_fields.get(name=name)
                    updated_field.field_type = field
                    updated_field.save()
                    django_field_for_db = updated_field.get_django_field()
                    django_field_for_db.column = name
                    schema_editor.alter_field(django_model, getattr(django_model, name).field, django_field_for_db)
                else:
                    new_field = Field.objects.create(model=model_to_be_updated, name=name, field_type=field)
                    django_field_for_db = new_field.get_django_field()
                    django_field_for_db.column = name
                    schema_editor.add_field(django_model, django_field_for_db)
        return {"model_id": model_id}


class DynamicModelRowSerializer(serializers.Serializer):
    fields = serializers.JSONField()

    def add_row(self, model_id):
        try:
            model_table = DynamicModelTable.objects.get(model_id=model_id)
        except DynamicModelTable.DoesNotExist:
            return {"error": f"Could not find model with ID of {model_id}."}
        
        table_fields = model_table.fields.order_by("name")
        fields_data = self.validated_data.get("fields")
        django_model = model_table.get_django_model()
        new_object = django_model.objects.create(**fields_data)
        return {"status": "OK"}
