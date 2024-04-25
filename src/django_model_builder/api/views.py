from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework import serializers
from api.serializers import DynamicModelSerializer, DynamicModelRowSerializer, create_serializer_for_model
from api.models import DynamicModelTable, Field
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer
from django.http import Http404
from drf_spectacular.extensions import OpenApiViewExtension
import ast
import json
import uuid


def string_is_valid_uuid(string):
    try:
        uuid.UUID(string)
    except ValueError:
        return False
    return True


@extend_schema(
    examples = [
         OpenApiExample(
            'Valid table creation example',
            summary='Valid dynamic model structure',
            description='The only input field is \'fields\', which takes a dictionary. ' \
                'The keys are the model field names, and the values are the field data types. ' \
                'There are three options: STR, NUM, and BOOL.',
            value={
                'fields': {
                    'name': "STR",
                    'age': "NUM",
                    "insured": "BOOL"
                }
            },
            request_only=True, # signal that example only applies to requests
        ),
        OpenApiExample(
            'Table creation 200 response',
            summary='Successful table creation response',
            description='',
            value={
                'fields': {
                    'model_id': uuid.uuid4(),
                }
            },
            response_only=True, # signal that example only applies to responses
        ),
    ]
)
class DynamicModelCreateView(GenericAPIView):
    """
    Create dynamic model.
    """
    serializer_class=DynamicModelSerializer
    queryset = DynamicModelTable.objects.none()

    def post(self, request, format=None):
        serializer = DynamicModelSerializer(data=request.data)
        if serializer.is_valid():
            new_model_id = serializer.save()
            return Response(new_model_id, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    examples = [
         OpenApiExample(
            'Valid table update example',
            summary='Valid dynamic model structure',
            description='As with the create view, fhe only input field is \'fields\', which takes a dictionary. ' \
                'The keys are the model field names, and the values are the field data types. ' \
                'There are three options: STR, NUM, and BOOL. ' \
                'The provided fields are checked against the existing model structure. ' \
                'new fields are added, and fields with the same name are dropped and replaced ' \
                'with the new field, but only if there was a data type change (e.g. from STR to NUM).',
            value={
                'fields': {
                    'name': "STR",
                    'age': "NUM",
                    "insured": "BOOL"
                }
            },
            request_only=True, # signal that example only applies to requests
        ),
        OpenApiExample(
            'Table update 200 response',
            summary='Successful table update response',
            description='',
            value={
                'fields': {
                    'model_id': uuid.uuid4(),
                }
            },
            response_only=True, # signal that example only applies to responses
        ),
    ]
)
class DynamicModelUpdateView(GenericAPIView):
    """
    Update dynamic model.
    """
    serializer_class = DynamicModelSerializer
    queryset = DynamicModelTable.objects.none()

    def get_object(self, model_id):
        if not string_is_valid_uuid(model_id):
            raise Http404
        try:
            return DynamicModelTable.objects.get(model_id=model_id)
        except DynamicModelTable.DoesNotExist:
            raise Http404
    
    def put(self, request, *args, **kwargs):
        model = self.get_object(self.kwargs.get("id"))
        serializer = DynamicModelSerializer(
            data=request.data,
            context={"model_id": model.model_id}
        )
        if serializer.is_valid():
            updated_model = serializer.update_model(model.model_id)
            return Response(updated_model, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    examples = [
         OpenApiExample(
            'Valid table row insertion example',
            summary='Valid dynamic model row',
            description='To add a row to a dynamic model, pass the \'fields\' argument. ' \
                'The keys are the model field names, and the values are the row values. ' \
                'dynamic model fields are nullable, so you can omit values. ' \
                'If there is an unexpected input field, or an incompatible value, an error is thrown.',
            value={
                "fields": {
                    "name": "Adam",
                    "age": 23,
                    "insured": "Foo" # error
                }
            },
            request_only=True, # signal that example only applies to requests
        ),
        OpenApiExample(
            'Table row insertion 200 response',
            summary='Successful table row insertion response',
            description='',
            value={
                'fields': {
                    'model_id': uuid.uuid4(),
                }
            },
            response_only=True, # signal that example only applies to responses
        ),
    ]
)
class DynamicModelAddRowView(GenericAPIView):
    """
    Add row to dynamic model table.
    """
    serializer_class = DynamicModelRowSerializer
    
    def get_object(self, model_id):
        if not string_is_valid_uuid(model_id):
            raise Http404
        try:
            return DynamicModelTable.objects.get(model_id=model_id)
        except DynamicModelTable.DoesNotExist:
            raise Http404
    
    def post(self, request, *args, **kwargs):
        model_table = self.get_object(self.kwargs.get("id"))

        serializer = DynamicModelRowSerializer(data=request.data, context={"model_table": model_table})
        if serializer.is_valid():
            result = serializer.save()
            if result.get("error"):
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    responses = {
        200: inline_serializer(
            name="DynamicModelRowResponse",
            fields={
                "name": serializers.CharField(),
                "age": serializers.IntegerField(),
                "insured": serializers.BooleanField(),
            },
        )
    },
    examples = [
         OpenApiExample(
            'Successful table data fetch example',
            summary='Successful table data fetch',
            description='To get dynamic model data, simply call a GET request with the model id. ' \
                'The view finds the relevant model, constructs a serializer dynamically, ' \
                'and processes the queryset data into a response.',
            request_only=True, # signal that example only applies to requests
        ),
        OpenApiExample(
            'Table row insertion 200 response',
            summary='Successful table row insertion response',
            description='This response assumes that a table ' \
                'with the columns \'name\', \'age\', and \'insured\' exists.',
            value= [
                    {
                        "name": "Adam",
                        "age": 23,
                        "insured": 0
                    },
                    {
                        "name": "Mike",
                        "age": 31,
                        "insured": 1
                    }
                ],
            response_only=True, # signal that example only applies to responses
        ),
    ]
)
class DynamicModelGetRowsView(GenericAPIView):
    """
    Get a dynamic model table's row data.
    """
    def get_object(self, model_id):
        if not string_is_valid_uuid(model_id):
            raise Http404
        try:
            return DynamicModelTable.objects.get(model_id=model_id)
        except DynamicModelTable.DoesNotExist:
            raise Http404
    
    def get_serializer_class(self):
        model = self.get_object(self.kwargs.get("id"))
        django_model = model.get_django_model()
        return create_serializer_for_model(django_model)

    def get_queryset(self):
        model = self.get_object(self.kwargs.get("id"))
        django_model = model.get_django_model()
        return django_model.objects.all()

    
    def get(self, request, *args, **kwargs):
        # get relevant Django model
        model_table = self.get_object(self.kwargs.get("id"))
        django_model = model_table.get_django_model()

        # create dict from queryset for serializer
        # (dynamically created model serializer won't accept a queryset)
        queryset = list(django_model.objects.all().values(*tuple(field.name for field in django_model._meta.get_fields())))
        serializer_class = self.get_serializer_class()
        model_serializer = serializer_class(data=queryset, many=True)
    
        if model_serializer.is_valid():
            return Response(model_serializer.data, status=status.HTTP_200_OK)
        
        return Response(model_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
