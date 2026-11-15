import pytest

from app.core.config import Settings

DEPLOYED = {
    "environment": "staging",
    "jwt_secret": "j" * 40,
    "mfa_encryption_key": "bmV3LWtleS1mb3ItdGVzdHMtb25seS0wMDAwMDAwMDA=",
    "s3_access_key": "",
    "s3_secret_key": "",
}


def test_database_url_is_built_from_parts_with_tls():
    s = Settings(
        **DEPLOYED, db_host="db.internal", db_user="shop", db_password="p@ss:/word", db_name="shop"
    )
    assert s.database_url == (
        "postgresql+psycopg://shop:p%40ss%3A%2Fword@db.internal:5432/shop?sslmode=require"
    )


def test_deployed_environment_refuses_local_s3_keys():
    with pytest.raises(ValueError, match="S3_ACCESS_KEY"):
        Settings(**{**DEPLOYED, "s3_access_key": "local"})


def test_deployed_environment_needs_real_secrets():
    with pytest.raises(ValueError, match="MFA_ENCRYPTION_KEY"):
        Settings(**{k: v for k, v in DEPLOYED.items() if k != "mfa_encryption_key"})
