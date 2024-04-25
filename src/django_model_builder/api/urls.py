from django.urls import path
from api.views import DynamicModelCreateView, DynamicModelUpdateView, DynamicModelAddRowView, DynamicModelGetRowsView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


urlpatterns = [
    path("table/", DynamicModelCreateView.as_view(), name="create_table"),
    path("table/<str:id>", DynamicModelUpdateView.as_view(), name="edit_table"),
    path("table/<str:id>/row", DynamicModelAddRowView.as_view(), name="add_table_row"),
    path("table/<str:id>/rows", DynamicModelGetRowsView.as_view(), name="get_table_rows"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("schema/docs/", SpectacularSwaggerView.as_view(url_name="api:schema")),
]
