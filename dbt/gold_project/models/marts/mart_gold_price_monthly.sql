select
    date_trunc('month', date)::date as month,
    avg(gold_price_egp) as gold_price_monthly

from {{ ref('int_gold_price_egp') }}

group by
    date_trunc('month', date)::date

order by
    month