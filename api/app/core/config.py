from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_name: str = "pdfdiff-turbo"
    database_url: str = "postgresql+asyncpg://pdfdiff:pdfdiff@localhost:5432/pdfdiff"
    celery_broker_url: str = "amqp://guest:guest@localhost:5672//"
    celery_result_backend: str = "rpc://"
    data_dir: str = "/data"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_exp_minutes: int = 5256000
    refresh_token_exp_days: int = 3650
    render_dpi: int = 150
    diff_threshold: int = 5
    tika_url: str = "http://tika:9998/tika"
    recaptcha_site_key: str = ""
    recaptcha_secret_key: str = ""
    recaptcha_min_score: float = 0.5
    recaptcha_action: str = "register"


settings = Settings()
