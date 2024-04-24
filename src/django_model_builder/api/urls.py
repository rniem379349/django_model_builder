from django.urls import path
from api.views import create_table, edit_table, get_table_rows, add_table_row

urlpatterns = [
    path("table/", create_table, name="create_table"),
    path("table/<str:id>", edit_table, name="edit_table"),
    path("table/<str:id>/row", add_table_row, name="add_table_row"),
    path("table/<str:id>/rows", get_table_rows, name="get_table_rows"),
]
