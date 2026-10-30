# Enterprise360 raw data
Downloaded 2026-10-30 (IST) into `data/raw/`. Row counts measured by me with pandas (rows excluding header). Checksums: `sha256sum`. Large data must stay out of git.

## olist/ — Brazilian E-Commerce Public Dataset by Olist
- Source: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- Download: downloaded via Kaggle public endpoint https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce (no login)
- License: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) — per Kaggle API metadata https://www.kaggle.com/api/v1/datasets/view/olistbr/brazilian-ecommerce. Non-commercial, share-alike.

| File | Rows (measured) | Bytes | sha256 |
|---|---|---|---|
| olist/brazilian-ecommerce.zip (archive) | – | – | 967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784 |
| olist/olist_customers_dataset.csv | 99441 | 9033957 | 983a422239e1712ded753b3bf9ecf47dc73f144d306029dcfa99e70a226883d2 |
| olist/olist_geolocation_dataset.csv | 1000163 | 61273883 | b514f6fc991b9566aeba02aa5d67e2c3630f034b60a0e05aa0d082a3b66d88d6 |
| olist/olist_order_items_dataset.csv | 112650 | 15438671 | 0bc4d068c4fe38cbb01bd90e8746e3c613fe7b4baef75fab7b0e329701c3e279 |
| olist/olist_order_payments_dataset.csv | 103886 | 5777138 | 4f713964f2815dbbaa40b9488268c55aac3627bfce5aa96cf58d1f3616de3cc0 |
| olist/olist_order_reviews_dataset.csv | 99224 | 14451670 | 012b61c7593e34f51fa614efdf802b9c7056ce6aae5307ddb93236e7cfc797d7 |
| olist/olist_orders_dataset.csv | 99441 | 17654914 | 8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf |
| olist/olist_products_dataset.csv | 32951 | 2379446 | 3e6569628a17fbc75fd206ee357b59e20364b9afa90f5b6cd5b4d624c58aa9cc |
| olist/olist_sellers_dataset.csv | 3095 | 174703 | 1f643d2b950373b85735e7794b20986f528d7a000432e7c6f9bcbb44d0846a0e |
| olist/product_category_name_translation.csv | 71 | 2613 | a81f0d1f27b27e7293f761bc79e3ce8f348ee39c4b3ed3e49bde38f478586278 |

## olist_marketing_funnel/ — Marketing Funnel by Olist
- Source: https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist
- Download: Kaggle public endpoint https://www.kaggle.com/api/v1/datasets/download/olistbr/marketing-funnel-olist
- License: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) — per https://www.kaggle.com/api/v1/datasets/view/olistbr/marketing-funnel-olist

| File | Rows (measured) | Bytes | sha256 |
|---|---|---|---|
| olist_marketing_funnel/marketing-funnel-olist.zip (archive) | – | – | d476efe8d16ab267ce10535859ed3dd2d6e186bbb50c9d405a1e7bc05c200171 |
| olist_marketing_funnel/olist_closed_deals_dataset.csv | 842 | 171352 | 1433f402d8fff00ca167579de641d9525f6e846368958c166f699ef1b0c31f3d |
| olist_marketing_funnel/olist_marketing_qualified_leads_dataset.csv | 8000 | 703836 | 5537753b7549ce4068e52e2402c29f2773c5375fc0575520ae8f3f301f666573 |

## uci_online_retail_ii/ — Online Retail II (UCI id 502, DOI 10.24432/C5CG6D)
- Source: https://archive.ics.uci.edu/dataset/502/online+retail+ii
- Download: UCI publisher download https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip; original xlsx kept, each sheet exported to CSV by me
- License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — stated on https://archive.ics.uci.edu/dataset/502/online+retail+ii

| File | Rows (measured) | Bytes | sha256 |
|---|---|---|---|
| uci_online_retail_ii/online_retail_ii.zip (archive) | – | – | 572e36277c2390fbfde10664750731e0a86f55e33470d91919085f0408e67bfb |
| uci_online_retail_ii/online_retail_II.xlsx | n/a(xlsx) | 45622278 | bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980 |
| uci_online_retail_ii/online_retail_II_Year_2009-2010.csv | 525461 | 46810498 | 17181af53059386e360acb2714218558ef526f84acacc768ebbdd3a35623d941 |
| uci_online_retail_ii/online_retail_II_Year_2010-2011.csv | 541910 | 48039783 | 9f3414a3d06748ef953051fa6e2e183b1591047bdfda95e99afd5888de28eb16 |

Cross-check: UCI Online Retail II measured 525,461 + 541,910 = 1,067,371 rows, matching UCI-stated 1,067,371 instances (https://archive.ics.uci.edu/api/dataset?id=502). Olist publisher describes ~100k orders (measured 99,441) and Marketing Funnel 8k MQLs (measured 8,000).

See `raw/SCHEMA.md` for columns and join keys.