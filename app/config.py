from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPENAI_API_KEY: str | None = None
    ADZUNA_APP_ID: str
    ADZUNA_APP_KEY: str
    SERPAPI_KEY: str | None = None
    JSEARCH_KEY: str | None = None

    DB_URL: str = "sqlite:///./jobs.db"

    DEFAULT_TITLES: list[str] = [
        "full stack developer", "software engineer", "frontend developer",
        "backend developer", "java developer", "react developer"
    ]
    CITIES: list[str] = [
        "Canada (All)", "Toronto, ON", "Vancouver, BC", "Montréal, QC",
        "Calgary, AB", "Ottawa, ON", "Edmonton, AB", "Winnipeg, MB",
        "Québec City, QC", "Hamilton, ON", "Kitchener, ON",
        "Victoria, BC", "Halifax, NS"
    ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
