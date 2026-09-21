#* this file it work to update data from last day we append to today

import os
import pandas as pd

from datetime import date, timedelta
from sqlalchemy import create_engine, text

from source import get_gold_chunk, get_frankfurter_chunk #to call function we made it to pick gold price between to times

##to get required env variables and raise error if not found
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
GOLDEN_API_KEY = get_required_env("GoldenApi_key")


engine = create_engine(
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)


def get_last_date(table_name):  # func to pass t_name and pick last day was append

    with engine.connect() as conn:

        result = conn.execute(
            text(f"SELECT MAX(date) FROM {table_name}")
        )

        last_date = result.scalar()#scalar to return the first column of the first row in the result set, or None if the result set is empty.

    return last_date


def main():
    # variables to store last date by name

    today = date.today()

    with engine.begin() as conn:    #*transaction context manager to ensure that all database operations within the block are treated as a single transaction. If any operation fails, the entire transaction will be rolled back, ensuring data integrity.

        gold_last_date = get_last_date("gold_prices")
        exchange_last_date = get_last_date("exchange_rates")

        print(f"Last gold date: {gold_last_date}")
        print(f"Last exchange date: {exchange_last_date}")


        if gold_last_date is None:
            raise RuntimeError(
                "gold_prices is empty. Initial backfill is required."
            )

        if exchange_last_date is None:
            raise RuntimeError(
                "exchange_rates is empty. Initial backfill is required."
            )

        
        #! this variables make to prepare v to start from the day after last day we was append

        gold_start_date = gold_last_date + timedelta(days=1)
        exchange_start_date = exchange_last_date + timedelta(days=1)


     

        if gold_start_date <= today:

            gold_data_df = get_gold_chunk(
                gold_start_date,
                today
            )

            print(f"New gold rows: {len(gold_data_df)}")

            if not gold_data_df.empty:

                gold_data_df["date"] = pd.to_datetime(
                    gold_data_df["date"]
                ).dt.date

                gold_data_df = gold_data_df.drop_duplicates( # handle if program run twice in same day to avoid duplicate data
                    subset=["date"],
                    keep="last"
                )

                upsert_gold = text("""
                    INSERT INTO gold_prices (date, price)
                    VALUES (:date, :price)
                    ON CONFLICT (date)
                    DO UPDATE SET
                        price = EXCLUDED.price
                """)

                for row in gold_data_df.itertuples(index=False):

                    conn.execute(
                        upsert_gold,
                        {
                            "date": row.date,
                            "price": row.price
                        }
                    )

        else:
            print("No new gold data")


        

        if exchange_start_date <= today:

            exchange_data_df = get_frankfurter_chunk(
                exchange_start_date,
                today
            )

            print(
                f"New exchange rows: "
                f"{len(exchange_data_df)}"
            )

            if not exchange_data_df.empty:

                exchange_data_df["date"] = pd.to_datetime(
                    exchange_data_df["date"]
                ).dt.date

                exchange_data_df = exchange_data_df.drop_duplicates( # the different between gold and exchange , exchange once in same day returned two prices for same day
                    
                    
                    subset=[
                        "date",
                        "base",
                        "quote",
                        "rate"
                    ],
                    keep="last"
                )

                upsert_exchange = text("""
                    INSERT INTO exchange_rates (
                        date,
                        base,
                        quote,
                        rate
                    )
                    VALUES (
                        :date,
                        :base,
                        :quote,
                        :rate
                    )
                    ON CONFLICT (date, rate)
                    DO NOTHING
                """)

                for row in exchange_data_df.itertuples(index=False):

                    conn.execute(
                        upsert_exchange,
                        {
                            "date": row.date,
                            "base": row.base,
                            "quote": row.quote,
                            "rate": row.rate
                        }
                    )

        else:
            print("No new exchange data")


if __name__ == "__main__":
    main()