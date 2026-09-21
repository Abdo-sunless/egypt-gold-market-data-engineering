select *
from {{ source('raw', 'fra_gold_investments') }}