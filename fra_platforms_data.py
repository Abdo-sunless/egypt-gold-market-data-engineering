import pandas as pd
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

fra_data = pd.read_excel(
    r"D:\fra_gold_investments.xlsx"
)
fra_data["period"] = pd.to_datetime(
    fra_data["period"]
).dt.date


fra_data.to_sql(
    "fra_gold_investments",
    con=engine,
    if_exists="append",
    index=False
)


print(f"Loaded {len(fra_data)} fra_gold_investments")