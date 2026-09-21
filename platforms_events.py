import pandas as pd
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()



def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value


POSTGRES_USER = get_required_env("POSTGRES_USER")
POSTGRES_PASSWORD = get_required_env("POSTGRES_PASSWORD")
POSTGRES_DB = get_required_env("POSTGRES_DB")
POSTGRES_HOST = get_required_env("POSTGRES_HOST")
POSTGRES_PORT = get_required_env("POSTGRES_PORT")


engine = create_engine(
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

platforms_events=pd.read_excel(r'D:\platform_events.xlsx') 

platforms_events["event_date"] = pd.to_datetime(
    platforms_events["event_date"]
).dt.date


platforms_events.to_sql(
    "platform_events",
    con=engine,
    if_exists="append",
    index=False
)


print(f"Loaded {len(platforms_events)} platform events")