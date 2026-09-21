select *
from {{ source('raw', 'gold_prices') }}