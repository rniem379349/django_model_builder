from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from api.serializers import DynamicModelSerializer, DynamicModelRowSerializer, create_serializer_for_model
from api.models import DynamicModelTable, Field
import ast
import json


@api_view(['POST'])
def create_table(request):
    """
    Create new model table. Returns new model's ID
    """
    if request.method == 'POST':
        serializer = DynamicModelSerializer(data=request.data)
        if serializer.is_valid():
            new_model_id = serializer.save()
            return Response(new_model_id, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
def edit_table(request, **kwargs):
    """
    Edit model table structure.
    """
    model_id = kwargs.get("id")
    try:
        model_to_be_updated = DynamicModelTable.objects.get(model_id=model_id)
    except DynamicModelTable.DoesNotExist:
        return Response({"error": f"Could not find model with ID of {model_id}."}, status=status.HTTP_404_NOT_FOUND)
    serializer = DynamicModelSerializer(
        data=request.data,
        context={"model_id": model_id}
    )
    if serializer.is_valid():
        updated_model = serializer.update_model(model_id)
        return Response(updated_model, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_table_rows(request, **kwargs):
    """
    Get a dynamic model table's row data.
    """
    # fetch model
    model_id = kwargs.get("id")
    try:
        model_table = DynamicModelTable.objects.get(model_id=model_id)
    except DynamicModelTable.DoesNotExist:
        return Response({"error": f"Could not find model with ID of {model_id}."}, status=status.HTTP_404_NOT_FOUND)
    django_model = model_table.get_django_model()
    # create dict from queryset for serializer
    # (dynamically created model serializer won't accept a queryset)
    queryset = list(django_model.objects.all().values(*tuple(field.name for field in django_model._meta.get_fields())))
    model_serializer_class = create_serializer_for_model(django_model)
    model_serializer = model_serializer_class(data=queryset, many=True)
    if model_serializer.is_valid():
        return Response(model_serializer.data, status=status.HTTP_200_OK)
    
    return Response(model_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
def add_table_row(request, **kwargs):
    """
    Add row to dynamic model table.
    """
    model_id = kwargs.get("id")
    try:
        model_table = DynamicModelTable.objects.get(model_id=model_id)
    except DynamicModelTable.DoesNotExist:
        return Response({"error": f"Could not find model with ID of {model_id}."}, status=status.HTTP_404_NOT_FOUND)

    serializer = DynamicModelRowSerializer(data=request.data, context={"model_table": model_table})
    if serializer.is_valid():
        result = serializer.save()
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
