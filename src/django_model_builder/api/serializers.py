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
        """
        Update a given model with the provided fields.
        Adds new fields.
        Existing fields are not touched unless there was a data type change.
        In that case, the field is replaces with a new one, with the new data type.
        """
        try:
            model_to_be_updated = DynamicModelTable.objects.get(model_id=model_id)
        except DynamicModelTable.DoesNotExist:
            return {"error": f"Could not find model with ID of {model_id}."}
        
        current_model_fields = model_to_be_updated.fields
        fields_data = self.validated_data.get('fields', {}).items()

        with connection.schema_editor() as schema_editor:
            django_model = model_to_be_updated.get_django_model()
            # Go over the provided fields and add/update the model's fields accordingly
            for name, field in fields_data:
                # if editing existing field, remove it first
                if (name,) in current_model_fields.values_list("name"):
                    # delete the column only if field type has changed
                    field_type_changed = current_model_fields.get(name=name).field_type != field
                    if not field_type_changed:
                        continue
                    Field.objects.filter(model=model_to_be_updated, name=name).delete()
                    schema_editor.remove_field(django_model, getattr(django_model, name).field)

                # this gets triggered for new fields 
                # and existing fields with a changed data type
                new_field = Field.objects.create(model=model_to_be_updated, name=name, field_type=field)
                django_field_for_db = new_field.get_django_field()
                django_field_for_db.column = name
                schema_editor.add_field(django_model, django_field_for_db)
        return {"model_id": model_id}


class DynamicModelRowSerializer(serializers.Serializer):
    fields = serializers.JSONField()

    def validate_fields(self, value):
        """
        Check if all provided fields exist in the targeted model.
        """
        model_table = self.context.get("model_table", None)
        if not model_table:
            raise serializers.ValidationError("This serializer needs a model table object.")
        
        django_model_fields = model_table.fields.all()
        for field_name, field_val in value.items():
            if not django_model_fields.filter(name=field_name).exists():
                raise serializers.ValidationError("Field '{}' not found in model.".format(field_name))
        return value
    
    def create(self, validated_data):
        """
        add data row to table.
        """
        # get dynamic model
        model_table = self.context.get("model_table", None)
        if not model_table:
            raise serializers.ValidationError("This serializer needs a model table object.")
        
        model_id = model_table.model_id
        django_model = model_table.get_django_model()
        
        # Try to insert the data row
        fields_data = validated_data.get('fields', {})
        try:
            new_row = django_model.objects.create(**fields_data)
        except Exception as e:
            return {"error": e.messages}
        return {"model_id": model_id}
