from django.core.validators import ValidationError
from django.db import models, connection
from django.db.utils import ProgrammingError


class FieldType(models.TextChoices):
    STRING = "STR", "String"
    NUMBER = "NUM", "Number"
    BOOLEAN = "BOOL", "Boolean"


class DynamicModelFactory:
    def create_model(self, name, fields=None, options=None):
        """
        Dynamically create specified model with provided model fields and Meta options.
        """
        class Meta:
            app_label = "api"

        # Update Meta with any options that were provided
        if options is not None:
            for key, value in options.iteritems():
                setattr(Meta, key, value)

        # Set up a dictionary to simulate declarations within a class
        attrs = {'__module__': __name__, 'Meta': Meta}

        # Add in any fields that were provided
        if fields:
            attrs.update(fields)

        # Create the class, which automatically triggers ModelBase processing
        model = type(name, (models.Model,), attrs)
        self.save_model_in_db(model)
        return model
    
    def save_model_in_db(self, model):
        """
        Given a Django model, try to save it in the database.
        Skips creation if model already present in DB.
        """
        try:
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(model)
        # catch case where db already created the model table earlier
        # which results in a django.db.utils.ProgrammingError
        except ProgrammingError:
            pass


class App(models.Model):
    """
    App model to associate dynamic models with.
    """
    name = models.CharField(max_length=255)
    module = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class DynamicModelTable(models.Model):
    """
    A Django model which records dynamically created tables.
    Used to keep a reference to dynamic models in the ORM
    """
    app = models.ForeignKey(App, related_name='models', on_delete=models.CASCADE)
    # model_id functions as the model name
    model_id = models.UUIDField(blank=False)

    class Meta:
        unique_together = (('app', 'model_id'),)
    
    # def __str__(self):
    #     return self.model_id

    def get_django_model(self):
        """
        Returns a functional Django model based on current data
        """
        # Get all associated fields into a list ready for dict()
        fields = [(f.name, f.get_django_field()) for f in self.fields.all()]

        # Use the create_model function defined above
        return DynamicModelFactory().create_model(str(self.model_id), dict(fields))


def is_valid_field(self, field_data, all_data):
    """
    Custom validator which checks if the provided field is a Django
    """
    if getattr(models, field_data) in FieldType:
        # It exists and is a proper field type
        return
    raise ValidationError(f"'{field_data}' is not a valid field type.")


class Field(models.Model):
    """
    Dynamic model field.
    """
    model = models.ForeignKey(DynamicModelTable, related_name='fields', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    field_type = models.CharField(max_length=255, validators=[is_valid_field])

    class Meta:
        unique_together = (('model', 'name'),)
    
    def get_django_field(self):
        """
        Given the object's field_type attribute, map it to a Django model field.
        """
        match self.field_type:
            case FieldType.STRING:
                django_field = models.CharField(max_length=150, null=True)
            case FieldType.NUMBER:
                django_field = models.IntegerField(null=True)
            case FieldType.BOOLEAN:
                django_field = models.BooleanField(null=True)
            case _:
                raise ValidationError(
                    f"Could not resolve field_type {self.field_type} into a Django model field."
                )
        return django_field
