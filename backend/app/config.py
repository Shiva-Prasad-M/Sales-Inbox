import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/alumnx_inbox"
    )

    GEMINI_API_KEY: str = os.getenv(
        "GEMINI_API_KEY",
        ""
    )

    CANDIDATE_ID: str = os.getenv(
        "CANDIDATE_ID",
        ""
    ).strip().lower()

    FRONTEND_URL: str = os.getenv(
        "FRONTEND_URL",
        "http://localhost:5173"
    )


settings = Settings()