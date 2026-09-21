import os
import time

import pandas as pd
from dotenv import load_dotenv
from pytrends.request import TrendReq
from sqlalchemy import create_engine, text


load_dotenv()

#*to get required env variables and raise error if not found
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

# create a SQLAlchemy engine to connect to the PostgreSQL database
engine = create_engine(
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)


def get_trends(start_date: str, end_date: str) -> pd.DataFrame:

    # Google Trends is divided by analytical purpose.
    #
    # Batch 1: General gold interest
    # Batch 2: Gold investment intent
    # Batch 3-4: Platform / product interest
    
    batches = [
        [
            "سعر الذهب",
            "الذهب اليوم",
            "عيار 21",
        ],
        [
            "استثمار الذهب",
            "شراء الذهب",
            "صندوق الذهب",
        ],
        [
            "ثاندر",
            "تطبيق ثاندر",
        ],
        [
            "تطبيق سبيكة",
            "صندوق ازيموت",
            "ازيموت جولد",
            "دهب ثاندر",
        ],
    ]

    trends_data = []
    #create a TrendReq object to interact with the Google Trends API

    for batch_id, keywords in enumerate(batches, start=1):

        pytrends = TrendReq(
            hl="ar",
            tz=180,
            timeout=(10, 30),
        )
        #handle exceptions to prevent the program from crashing if an error occurs while fetching data from the Google Trends API

        try:

            pytrends.build_payload(
                kw_list=keywords,
                timeframe=f"{start_date} {end_date}",
                geo="EG",
            )

            trends_df = pytrends.interest_over_time()

            if trends_df.empty:
                print(
                    f"Batch {batch_id}: no data returned"
                )
                time.sleep(2)
                continue

            trends_df = trends_df.reset_index()

            if "isPartial" in trends_df.columns:
                trends_df = trends_df.drop(
                    columns=["isPartial"]
                )

            trends_df["batch_id"] = batch_id
            trends_df["geo"] = "EG"

            # Convert this batch to long format BEFORE combining batches.
            # This prevents unrelated keywords from becoming NaN columns
            # inside other batches.
            trends_df = trends_df.melt(
                id_vars=[
                    "date",
                    "batch_id",
                    "geo",
                ],
                value_vars=keywords,
                var_name="keyword",
                value_name="interest",
            )

            trends_data.append(trends_df)

            print(
                f"Batch {batch_id}: success - "
                f"{len(trends_df)} rows"
            )

        except Exception as e:

            print(
                f"Batch {batch_id} failed: {e}"
            )

        # Small pause to reduce the chance of rate limiting.
        time.sleep(2)

    if not trends_data:
        return pd.DataFrame()

    trends_df = pd.concat(
        trends_data,
        ignore_index=True,
    )

    return trends_df


def load_trends(trends_df: pd.DataFrame) -> None:

    if trends_df.empty:
        raise RuntimeError(
            "No Google Trends data to load."
        )

    insert_sql = text(
        """
        INSERT INTO google_trends (
            date,
            batch_id,
            geo,
            keyword,
            interest
        )
        VALUES (
            :date,
            :batch_id,
            :geo,
            :keyword,
            :interest
        )
        ON CONFLICT (date, batch_id, keyword, geo)
        DO NOTHING
        """
    )

    with engine.begin() as conn:

        for row in trends_df.itertuples(index=False):

            conn.execute(
                insert_sql,
                {
                    "date": pd.to_datetime(
                        row.date
                    ).date(),

                    "batch_id": row.batch_id,

                    "geo": row.geo,

                    "keyword": row.keyword,

                    "interest": row.interest,
                },
            )

    print(
        f"Loaded {len(trends_df)} trend rows"
    )


if __name__ == "__main__":

    df = get_trends(
        "2019-01-01",
        "2026-08-31",
    )

    if df.empty:
        raise RuntimeError(
            "No Google Trends data was extracted."
        )

    print(
        f"\nExtracted rows: {len(df)}"
    )

    print(
        "\nRows by batch:"
    )

    print(
        df.groupby("batch_id").size()
    )

    print(
        "\nKeywords by batch:"
    )

    print(
        df[
            ["batch_id", "keyword"]
        ]
        .drop_duplicates()
        .sort_values(
            ["batch_id", "keyword"]
        )
        .to_string(index=False)
    )

    print(
        "\nInterest summary:"
    )

    print(
        df.groupby("keyword")["interest"]
        .agg(
            count="count",
            min="min",
            max="max",
            mean="mean",
        )
        .sort_index()
        .to_string()
    )

    load_trends(df)

