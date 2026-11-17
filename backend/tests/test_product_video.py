import pytest

from app.core.config import get_settings
from tests.test_catalog import create_product, publish, upload

MP4 = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41" + b"\x00" * 200
WEBM = (
    b"\x1a\x45\xdf\xa3\x9f\x42\x86\x81\x01\x42\xf7\x81\x01\x42\xf2\x81\x04\x42\xf3\x81\x08\x42\x82\x84webm"
    + b"\x00" * 200
)
MOV = b"\x00\x00\x00\x14ftypqt  \x00\x00\x02\x00qt  " + b"\x00" * 200


@pytest.fixture
def admin(client, staff_token):
    from tests.helpers import auth

    return auth(staff_token("Admin"))


@pytest.fixture
def category(client, admin):
    return client.post("/api/v1/admin/categories", json={"name": "Bottles"}, headers=admin).json()


def video(client, admin, product_id, data=MP4, name="clip.mp4", ctype="video/mp4", alt=""):
    return client.post(
        f"/api/v1/admin/products/{product_id}/videos",
        files={"file": (name, data, ctype)},
        data={"alt_text": alt},
        headers=admin,
    )


def test_mp4_and_webm_are_stored_and_shown_after_the_pictures(client, admin, category, storage):
    product = create_product(client, admin, category)
    upload(client, admin, product["id"])
    resp = video(client, admin, product["id"], alt="Bottle being filled")
    assert resp.status_code == 201, resp.text
    resp = video(client, admin, product["id"], WEBM, "clip.webm", "video/webm")
    media = resp.json()["media"]
    assert [m["type"] for m in media] == ["IMAGE", "VIDEO", "VIDEO"]
    assert media[1]["url"].endswith(".mp4") and media[1]["alt_text"] == "Bottle being filled"
    assert media[2]["url"].endswith(".webm") and not media[2]["is_primary"]
    stored = {k: v[1] for k, v in storage.objects.items()}
    assert sorted(stored.values()) == ["image/png", "video/mp4", "video/webm"]

    publish(client, admin, product["id"])
    public = client.get(f"/api/v1/products/{product['slug']}").json()
    assert [m["type"] for m in public["media"]] == ["IMAGE", "VIDEO", "VIDEO"]
    assert public["image_url"] == media[0]["url"]  # the card keeps the picture


def test_the_file_contents_decide_not_its_name(client, admin, category, storage):
    product = create_product(client, admin, category)
    fake = video(client, admin, product["id"], b"not a video at all" * 10, "clip.mp4")
    assert fake.status_code == 415
    mov = video(client, admin, product["id"], MOV, "clip.mov", "video/quicktime")
    assert mov.status_code == 415 and "MP4" in mov.json()["error"]["message"]
    assert storage.objects == {}


def test_size_and_count_limits(client, admin, category, monkeypatch):
    product = create_product(client, admin, category)
    monkeypatch.setattr(get_settings(), "max_video_bytes", 100)
    big = video(client, admin, product["id"])
    assert big.status_code == 413
    assert video(client, admin, product["id"], b"").status_code == 422
    monkeypatch.undo()
    for _ in range(3):
        assert video(client, admin, product["id"]).status_code == 201
    fourth = video(client, admin, product["id"])
    assert fourth.status_code == 409 and fourth.json()["error"]["code"] == "too_many_videos"


def test_removing_the_primary_picture_never_makes_a_video_primary(client, admin, category):
    product = create_product(client, admin, category)
    first = upload(client, admin, product["id"]).json()["media"][0]
    video(client, admin, product["id"])
    upload(client, admin, product["id"])
    publish(client, admin, product["id"])
    resp = client.delete(
        f"/api/v1/admin/products/{product['id']}/media/{first['id']}", headers=admin
    )
    assert resp.status_code == 200, resp.text
    media = resp.json()["media"]
    primary = [m for m in media if m["is_primary"]]
    assert len(primary) == 1 and primary[0]["type"] == "IMAGE"

    # The last picture can't go while published, even with a video left.
    last = primary[0]["id"]
    resp = client.delete(f"/api/v1/admin/products/{product['id']}/media/{last}", headers=admin)
    assert resp.status_code == 400 and resp.json()["error"]["code"] == "last_image"


def test_manager_cannot_upload_videos(client, staff_token, admin, category):
    from tests.helpers import auth

    product = create_product(client, admin, category)
    manager = auth(staff_token("Manager"))
    assert video(client, manager, product["id"]).status_code == 403
