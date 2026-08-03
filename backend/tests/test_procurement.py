def test_list_suppliers(client):
    response = client.get("/api/v1/suppliers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_supplier_not_found(client):
    response = client.get("/api/v1/suppliers/999999")
    assert response.status_code == 404


def test_supplier_performance(client):
    response = client.get("/api/v1/suppliers/1/performance")
    assert response.status_code == 200
    data = response.json()
    assert "on_time_rate_pct" in data
    assert "total_purchase_orders" in data


def test_list_purchase_requests(client):
    response = client.get("/api/v1/procurement/purchase-requests")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_purchase_orders(client):
    response = client.get("/api/v1/procurement/purchase-orders")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_late_purchase_orders(client):
    response = client.get("/api/v1/procurement/purchase-orders?is_late=true")
    assert response.status_code == 200
    data = response.json()
    for po in data:
        assert po["is_late"] is True
