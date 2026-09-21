import os

from datetime import date, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine

from source import get_gold_chunk, get_frankfurter_chunk


load_dotenv()


POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")


engine = create_engine(
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)


START_DATE = date(2019, 1, 1)
END_DATE = date(2026, 8, 16)


def main():

    current_date = START_DATE

    while current_date <= END_DATE:

        loop_end = min(
            current_date + timedelta(days=89),
            END_DATE
        )

        print(f"Processing {current_date} → {loop_end}")

        gold_data_df = get_gold_chunk(
            current_date,
            loop_end
        )

        exchange_data_df = get_frankfurter_chunk(
            current_date,
            loop_end
        )

        print(f"Gold rows: {len(gold_data_df)}")
        print(f"Exchange rows: {len(exchange_data_df)}")

        gold_data_df.to_sql(
            "gold_prices",
            con=engine,
            if_exists="append",
            index=False
        )

        exchange_data_df.to_sql(
            "exchange_rates",
            con=engine,
            if_exists="append",
            index=False
        )

        current_date = loop_end + timedelta(days=1)


if __name__ == "__main__":
    main()