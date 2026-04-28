from utils.path_normalization import normalize_request_path


def test_normalize_request_path_replaces_uuid_and_numeric_ids():
    path = "/api/projects/123/tasks/550e8400-e29b-41d4-a716-446655440000"

    assert normalize_request_path(path) == "/api/projects/{id}/tasks/{id}"


def test_normalize_request_path_preserves_non_id_segments():
    path = "/api/v1/projects/active/tasks/todo"

    assert normalize_request_path(path) == "/api/v1/projects/active/tasks/todo"
