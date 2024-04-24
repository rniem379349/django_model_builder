from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from api.models import DynamicModelTable, FieldType
from api.serializers import DynamicModelSerializer
import random
from uuid import uuid4


class DynamicModelTestMixin:
    """ Dynamic model test helper functions. """
    def create_table(self, data=None):
        """
        Create a new table.
        """
        url = reverse('api:create_table')
        data = data or {
            "fields": {
                "name": "STR",
                "age": "NUM"
            }
        }
        response = self.client.post(url, data, format="json")
        self.assertTrue(status.is_success(response.status_code))
        new_model_id = response.data.get("model_id")
        return new_model_id
    
    def add_table_row(self, model_id, data=None):
        """
        Add a table row.
        """
        data = data or {
            "fields": {
                "name": str(random.randint(1,1000)),
                "age": random.randint(1,100),
            }
        }
        url = reverse('api:add_table_row', kwargs={"id": model_id})
        response = self.client.post(url, data, format="json")
        self.assertTrue(status.is_success(response.status_code))
        return data
    
    def get_table_rows(self, model_id):
        url = reverse('api:get_table_rows', kwargs={"id": model_id})
        response = self.client.get(url, format="json")
        self.assertTrue(status.is_success(response.status_code))
        return response.data


class CreateTableTestCase(DynamicModelTestMixin, APITestCase):
    def test_create_table_ok(self):
        """
        Test create_table POST view with valid data.
        """
        model_id = self.create_table()
        # check model
        self.assertEqual(DynamicModelTable.objects.count(), 1)
        new_model = DynamicModelTable.objects.last()
        self.assertEqual(str(new_model.model_id), model_id)
        # check fields
        fields = new_model.fields.order_by("name")
        self.assertEqual(fields[0].name, "age")
        self.assertEqual(fields[0].field_type, FieldType.NUMBER)
        self.assertEqual(fields[1].name, "name")
        self.assertEqual(fields[1].field_type, FieldType.STRING)

    def test_create_table_error(self):
        """
        Test create_table POST view with invalid data (incorrect field type).
        """
        url = reverse('api:create_table')
        data = {
            "fields": {
                "name": "FOO", # incorrect option
                "age": "NUM"
            }
        }
        response = self.client.post(url, data, format="json")
        self.assertTrue(status.is_client_error(response.status_code))


class EditTableTestCase(DynamicModelTestMixin, APITestCase):
    def test_edit_table_ok(self):
        """
        Test successful edit of empty table.
        """
        new_model_id = self.create_table()

        # Edit the table
        data = {
            "fields": {
                "name": "STR",
                "age": "STR", # changed field type
                "insured": "BOOL", # new field
            }
        }
        url = reverse('api:edit_table', kwargs={"id": new_model_id})
        response = self.client.put(url, data, format="json")
        self.assertTrue(status.is_success(response.status_code))

        # check model
        self.assertEqual(DynamicModelTable.objects.count(), 1)
        updated_model = DynamicModelTable.objects.last()
        self.assertEqual(str(updated_model.model_id), new_model_id)
        # check fields
        fields = updated_model.fields.order_by("name")
        self.assertEqual(fields[0].name, "age")
        self.assertEqual(fields[0].field_type, FieldType.STRING)
        self.assertEqual(fields[1].name, "insured")
        self.assertEqual(fields[1].field_type, FieldType.BOOLEAN)
        self.assertEqual(fields[2].name, "name")
        self.assertEqual(fields[2].field_type, FieldType.STRING)

    def test_edit_table_existing_data(self):
        """
        Test successful edit of table with data rows.
        """
        # create table and populate it
        new_model_id = self.create_table()
        row_1 = self.add_table_row(new_model_id)
        row_2 = self.add_table_row(new_model_id)

        # Check the table rows
        row_data = self.get_table_rows(new_model_id)
        self.assertIn({'name': row_1["fields"]["name"], "age": row_1["fields"]["age"]}, row_data)
        self.assertIn({'name': row_2["fields"]["name"], "age": row_2["fields"]["age"]}, row_data)

        # Edit the table
        data = {
            "fields": {
                "name": "BOOL", # changed field type from str to bool
                "age": "NUM", # no change
            }
        }
        url = reverse('api:edit_table', kwargs={"id": new_model_id})
        response = self.client.put(url, data, format="json")
        self.assertTrue(status.is_success(response.status_code))

        # Check the table rows again. The 'age' values should be the same,
        # And the 'name' values should be nulled out due to a field type change.
        row_data = self.get_table_rows(new_model_id)
        self.assertIn({'name': None, "age": row_1["fields"]["age"]}, row_data)
        self.assertIn({'name': None, "age": row_2["fields"]["age"]}, row_data)

    
    def test_edit_table_incorrect_model_id(self):
        """
        Test edit_table POST view with invalid model id.
        """
        model_id = uuid4()

        # Edit the table
        data = {
            "fields": {
                "name": "STR",
                "age": "STR", # changed field type
                "insured": "BOOL", # new field
            }
        }
        url = reverse('api:edit_table', kwargs={"id": model_id})
        response = self.client.put(url, data, format="json")
        self.assertTrue(status.is_client_error(response.status_code))


class AddTableRowTestCase(DynamicModelTestMixin, APITestCase):
    def test_add_table_row_ok(self):
        """
        Test successful dynamic table row creation.
        """
        model_id = self.create_table()

        # Add new row
        data = {
            "fields": {
                "name": "Adam",
                "age": 23,
            }
        }
        self.add_table_row(model_id, data)

        django_model = DynamicModelTable.objects.last().get_django_model()
        self.assertEqual(django_model.objects.count(), 1)
        new_row = django_model.objects.last()
        self.assertEqual(new_row.name, "Adam")
        self.assertEqual(new_row.age, 23)
    

    def test_add_table_row_incorrect_model_id(self):
        """
        Test add table row POST view with invalid model id.
        """
        model_id = uuid4()

        # Add new row
        data = {
            "fields": {
                "name": "Adam",
                "age": 23,
            }
        }
        url = reverse('api:add_table_row', kwargs={"id": model_id})
        response = self.client.post(url, data, format="json")
        self.assertTrue(status.is_client_error(response.status_code))

    def test_add_table_row_error_unexpected_field(self):
        """
        Test row creation error due to unexpected input field.
        """
        model_id = self.create_table()

        # Add new row
        data = {
            "fields": {
                "name": "Adam",
                "age": 23,
                "insured": True
            }
        }
        url = reverse('api:add_table_row', kwargs={"id": model_id})
        response = self.client.post(url, data, format="json")
        self.assertTrue(status.is_client_error(response.status_code))
        self.assertEqual(str(response.data["fields"][0]), "Field 'insured' not found in model.")

    def test_add_table_row_error_wrong_data_type(self):
        """
        Test row creation error due to incorrect data type.
        """
        table_data = {
            "fields": {
                "name": "STR",
                "age": "NUM",
                "insured": "BOOL"
            }
        }
        model_id = self.create_table(data=table_data)

        # Add new row
        data = {
            "fields": {
                "name": "Adam",
                "age": 23,
                "insured": "Foo" # error
            }
        }
        url = reverse('api:add_table_row', kwargs={"id": model_id})
        response = self.client.post(url, data, format="json")
        self.assertTrue(status.is_client_error(response.status_code))
        self.assertIn("value must be either True, False, or None.", response.data["error"][0])


class GetTableRowsTestCase(DynamicModelTestMixin, APITestCase):
    def test_get_table_rows_ok(self):
        """
        Test successful dynamic table data fetching.
        """
        model_id = self.create_table()

        # Add some rows
        row_1 = self.add_table_row(model_id)
        row_2 = self.add_table_row(model_id)

        data = self.get_table_rows(model_id)
        # Check table rows
        self.assertIn({'name': row_1["fields"]["name"], "age": row_1["fields"]["age"]}, data)
        self.assertIn({'name': row_2["fields"]["name"], "age": row_2["fields"]["age"]}, data)
    
    def test_get_table_rows_error_incorrect_model_id(self):
        """
        Test non-existent model id error handling.
        """
        model_id = uuid4()

        url = reverse('api:get_table_rows', kwargs={"id": model_id})
        response = self.client.get(url, format="json")
        self.assertTrue(status.is_client_error(response.status_code))
