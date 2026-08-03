def test_list_projects(client):
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_list_projects_filter_status(client):
    response = client.get("/api/v1/projects?status=Active")
    assert response.status_code == 200
    data = response.json()
    for p in data:
        assert p["status"] == "Active"


def test_get_project_not_found(client):
    response = client.get("/api/v1/projects/999999")
    assert response.status_code == 404


def test_list_project_risks_empty(client):
    response = client.get("/api/v1/projects/1/risks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
