from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./migration_factory.db"
    cors_origins: str = "http://localhost:5173"
    nutanix_pc_url: str = ""
    nutanix_username: str = ""
    nutanix_password: str = ""
    nutanix_verify_tls: bool = True

    auth_enabled: bool = False
    viewer_api_key_sha256: str = ""
    operator_api_key_sha256: str = ""
    approver_api_key_sha256: str = ""
    admin_api_key_sha256: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
