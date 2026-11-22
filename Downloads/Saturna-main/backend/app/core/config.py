import logging
import secrets
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_name: str = "Saturna API"
    database_url: str = "sqlite:///./saturna.db"
    environment: Literal["development", "test", "production"] = "development"
    jwt_secret: str = Field(default="", validation_alias="JWT_SECRET")
    access_minutes: int = Field(default=30, ge=1, validation_alias="JWT_ACCESS_MINUTES")
    refresh_days: int = Field(default=7, ge=1, validation_alias="JWT_REFRESH_DAYS")
    qr_token_ttl_hours: int = Field(default=24, ge=1, le=168, validation_alias="QR_TOKEN_TTL_HOURS")
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    public_base_url: str = "http://localhost:8000"

    # WhatsApp Cloud API (si WHATSAPP_TOKEN está vacío se usa el modo simulado)
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_verify_token: str = "saturna-verify"
    whatsapp_app_secret: str = ""
    whatsapp_template_arrival: str = "aviso_llegada"
    whatsapp_template_lang: str = "es"
    whatsapp_graph_version: str = "v21.0"

    # Modelo de lenguaje (si LLM_API_KEY está vacío se usa el agente offline por reglas)
    llm_api_key: str = ""
    llm_model: str = "claude-haiku-5-5"

    default_country_code: str = "591"  # Bolivia

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        example_values = {
            "cambia-esto-en-produccion",
            "cambia-esto-por-una-cadena-larga-y-aleatoria",
            "CAMBIAR_POR_UN_SECRETO_ALEATORIO_DE_32_CARACTERES",
        }
        if self.environment == "production":
            if not self.jwt_secret or self.jwt_secret in example_values:
                raise RuntimeError("JWT_SECRET debe configurarse en producción")
            if len(self.jwt_secret) < 32:
                raise RuntimeError("JWT_SECRET debe tener al menos 32 caracteres en producción")
        elif not self.jwt_secret or self.jwt_secret in example_values:
            if self.environment == "test":
                self.jwt_secret = "saturna-test-secret-32-bytes-minimo"
            else:
                self.jwt_secret = secrets.token_urlsafe(48)
                logging.getLogger("saturna.config").warning(
                    "JWT_SECRET no configurado; se generó una clave efímera. Las sesiones se perderán al reiniciar."
                )
        elif len(self.jwt_secret) < 32:
            if self.environment == "test":
                self.jwt_secret = "saturna-test-secret-32-bytes-minimo"
            else:
                raise RuntimeError("JWT_SECRET debe tener al menos 32 caracteres")
        return self

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
