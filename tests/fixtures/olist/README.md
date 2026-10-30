# Olist test fixtures
Hand-written, FK-consistent miniature of the 9 Olist files (same headers, quoting style and quirks).
Values are synthetic test inputs, NOT Olist records, and never feed any report. Edge cases covered:
- one person (customer_unique_id u..1) with two customer_ids/orders -> repeat customer
- canceled + unavailable orders (KPI_NET_GMV, KPI_CANCEL_RATE); order 4 has payment but no items
- order 2: late delivery, credit card + voucher split payment, two reviews (latest-review rule)
- review_id r..4 attached to two orders (review_id not unique alone); multi-line quoted message
- product with NULL category, category without English translation (pc_gamer)
- duplicate geolocation points, an out-of-Brazil point, seller zip 88010 without geolocation
- delivered order with NULL delivery timestamp (dq_missing_delivery_ts)
- translation file starts with a UTF-8 BOM (as the real file does)
