select *
from {{ source('raw', 'google_trends') }}