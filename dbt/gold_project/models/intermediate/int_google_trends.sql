with trends as (

    select
        date,
        batch_id,
        geo,
        keyword,
        interest
    from {{ ref('stg_google_trends') }}

),

monthly_trends as (

    select
        date_trunc('month', date)::date as month,
        batch_id,
        geo,
        keyword,
        interest
    from trends

)

select
    month,
    batch_id,
    geo,
    keyword,
    interest
from monthly_trends