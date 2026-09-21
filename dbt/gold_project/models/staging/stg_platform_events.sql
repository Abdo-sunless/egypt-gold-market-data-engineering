select *
from {{ source('raw', 'platform_events') }}