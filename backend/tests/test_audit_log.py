import pytest

from tests.helpers import auth, published_product

LOGS = "/api/v1/admin/audit-logs"


@pytest.fixture
def admin(staff_token):
    return auth(staff_token("Admin"))


def test_lists_actions_newest_first_with_actor(client, admin):
    product = published_product(client, admin, name="Lamp")
    page = client.get(LOGS, headers=admin).json()
    assert page["total"] >= 2
    first = page["items"][0]
    assert first["actor_email"]
    times = [e["occurred_at"] for e in page["items"]]
    assert times == sorted(times, reverse=True)

    by_record = client.get(LOGS, params={"q": product["id"]}, headers=admin).json()
    assert by_record["total"] >= 1
    assert {e["entity_id"] for e in by_record["items"]} == {product["id"]}


def test_filters_by_action_and_actor(client, admin, staff_token):
    published_product(client, admin, name="Lamp")
    actions = client.get(f"{LOGS}/actions", headers=admin).json()
    assert actions == sorted(actions) and actions

    chosen = actions[0]
    filtered = client.get(LOGS, params={"action": chosen}, headers=admin).json()
    assert {e["action"] for e in filtered["items"]} == {chosen}

    email = filtered["items"][0]["actor_email"]
    mine = client.get(LOGS, params={"q": email}, headers=admin).json()
    assert {e["actor_email"] for e in mine["items"]} == {email}
    nobody = client.get(LOGS, params={"q": "no-such-person"}, headers=admin).json()
    assert nobody["total"] == 0


def test_date_filter(client, admin):
    published_product(client, admin, name="Lamp")
    future = client.get(LOGS, params={"date_from": "2999-01-01"}, headers=admin).json()
    assert future["total"] == 0
    past = client.get(LOGS, params={"date_to": "2000-01-01"}, headers=admin).json()
    assert past["total"] == 0
