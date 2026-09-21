import requests
import os
import pandas as pd
from dotenv import load_dotenv



load_dotenv()


GOLDEN_API_KEY = os.getenv("GoldenApi_key")


def get_gold_chunk(start_date, end_date):

    url = (
        f"https://www.goldapi.io/api/history/XAU/USD"
        f"?from={start_date}&to={end_date}"
    )

    headers = {
        "x-access-token": GOLDEN_API_KEY
    }

    response = requests.get(
        url,
        headers=headers
    )

    response.raise_for_status()

    data = response.json()

    return pd.DataFrame(data["prices"])


def get_frankfurter_chunk(start_date, end_date):

    url = (
        f"https://api.frankfurter.dev/v2/rates"
        f"?from={start_date}&to={end_date}"
        f"&base=USD&quotes=EGP"
    )

    response = requests.get(url)

    response.raise_for_status()

    data = response.json()

    return pd.DataFrame(data)

