# django_model_builder
A dynamic model builder API, build using Django and DRF.

## Features
- DRF's browsable API,
- Documentation using `drf_spectacular` including examples,
- API Tests.

## Setup
1. Clone the repo,
2. In the root directory, run `make migrate`,
3. run `docker compose up`.

## Getting started
A documentation page with examples can be found at `/api/schema/docs`.

Here is a sample workflow:
1. Navigate to `http://localhost:8080/api/table` (create table view),
2. In the browsable API's `Content` field, put `{"fields": {"name": "STR","age": "NUM"}}`,
3. If successful, the response should carry the new model's ID. Copy it.
4. Go to `http://localhost:8080/api/table/<model_id>/row` (add table row view). Make sure to paste the model id in the appropriate place,
5. In the browsable API's `Content` field, put `{"fields":{"age":32,"name":"Mike"}}`,
6. Go to `http://localhost:8080/api/table/<model_id>/rows` (get table rows view) and check if the row was added,
7. Go to `http://localhost:8080/api/table/<model_id>` (update table view),
8. In the browsable API's `Content` field, put `{"fields": {"name": "STR","age": "NUM", "insured": "BOOL"}}`,
9. go back to `http://localhost:8080/api/table/<model_id>/rows` (get table rows view) and check if the new column was added.
