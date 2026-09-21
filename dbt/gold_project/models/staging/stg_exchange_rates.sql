select *
from {{ source('raw', 'exchange_rates') }}