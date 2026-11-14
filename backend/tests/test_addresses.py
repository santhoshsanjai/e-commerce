from tests.helpers import ADDRESS, auth


def test_first_address_becomes_default_and_default_moves(client, buyer_token):
    h = auth(buyer_token())
    first = client.post("/api/v1/me/addresses", json=ADDRESS, headers=h).json()
    assert first["is_default"] is True
    assert first["country_code"] == "IN"
    second = client.post(
        "/api/v1/me/addresses",
        json={**ADDRESS, "line1": "9 Park St", "is_default": True},
        headers=h,
    ).json()
    listed = client.get("/api/v1/me/addresses", headers=h).json()
    assert [a["id"] for a in listed] == [second["id"], first["id"]]
    assert [a["is_default"] for a in listed] == [True, False]


def test_deleting_default_promotes_another(client, buyer_token):
    h = auth(buyer_token())
    first = client.post("/api/v1/me/addresses", json=ADDRESS, headers=h).json()
    second = client.post("/api/v1/me/addresses", json=ADDRESS, headers=h).json()
    assert client.delete(f"/api/v1/me/addresses/{first['id']}", headers=h).status_code == 204
    (remaining,) = client.get("/api/v1/me/addresses", headers=h).json()
    assert remaining["id"] == second["id"] and remaining["is_default"] is True


def test_invalid_pin_code_and_phone_rejected(client, buyer_token):
    h = auth(buyer_token())
    for bad in ({"postal_code": "012345"}, {"postal_code": "5600"}, {"phone": "abc"}):
        assert (
            client.post("/api/v1/me/addresses", json={**ADDRESS, **bad}, headers=h).status_code
            == 422
        )


def test_cannot_read_or_change_another_buyers_address(client, buyer_token):
    owner = auth(buyer_token())
    other = auth(buyer_token())
    address = client.post("/api/v1/me/addresses", json=ADDRESS, headers=owner).json()
    assert client.get("/api/v1/me/addresses", headers=other).json() == []
    assert (
        client.put(f"/api/v1/me/addresses/{address['id']}", json=ADDRESS, headers=other).status_code
        == 404
    )
    assert client.delete(f"/api/v1/me/addresses/{address['id']}", headers=other).status_code == 404


def test_staff_cannot_use_buyer_endpoints(client, staff_token):
    h = auth(staff_token("Super Admin"))
    assert client.get("/api/v1/me/addresses", headers=h).status_code == 403
    assert client.get("/api/v1/cart", headers=h).status_code == 403
