with gold as (

    select
        date,
        price
    from {{ ref('stg_Gold_price') }}

),

exchange as (

    select
        date,
        avg(rate) as rate
    from {{ ref('stg_exchange_rates') }}
    where base = 'USD'
      and quote = 'EGP'
    group by date

)

select
    g.date,
    g.price as gold_price_usd,
    e.rate as usd_egp,
    g.price * e.rate as gold_price_egp

from gold g
join exchange e
    on g.date = e.date