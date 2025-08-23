import os
from dataclasses import dataclass

@dataclass
class Settings:
    # Polygon
    POLYGON_API_KEY: str = os.getenv("POLYGON_API_KEY", "")

    # InfluxDB v2
    INFLUX_URL: str = os.getenv("INFLUX_URL", "http://localhost:8086")
    INFLUX_TOKEN: str = os.getenv("INFLUX_TOKEN", "")
    INFLUX_ORG: str = os.getenv("INFLUX_ORG", "primary")
    INFLUX_BUCKET: str = os.getenv("INFLUX_BUCKET", "market_data")

    # Streaming
    STREAM_SYMBOLS: str = os.getenv("STREAM_SYMBOLS", "X:BTCUSD")
    WS_BIND_HOST: str = os.getenv("WS_BIND_HOST", "0.0.0.0")
    WS_BIND_PORT: int = int(os.getenv("WS_BIND_PORT", "8081"))

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")           # Flask secret (and fallback for JWT)
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")           # Preferred JWT secret if set
    JWT_ISSUER: str = os.getenv("JWT_ISSUER", "")
    JWT_AUDIENCE: str = os.getenv("JWT_AUDIENCE", "")
    JWT_ACCESS_TTL_MIN: int = int(os.getenv("JWT_ACCESS_TTL_MIN", "30"))

    # Mongo
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/your_database")

settings = Settings()