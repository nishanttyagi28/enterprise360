# Marketing Funnel fixtures
Synthetic miniature (same headers as Kaggle olistbr/marketing-funnel-olist; NOT real records). 6 leads,
3 deals. Covers: a null origin (-> dim_lead_origin 'not_recorded'), the source value 'unknown', a deal
whose seller_id exists in the Olist sellers fixture (match) and two that do not, a quoted multi-value
lead_behaviour_profile, has_company/has_gtin booleans, and one deal won BEFORE first contact (mql 6,
the warn test). Used by CI (`python -m ingestion funnel` with E360_FUNNEL_DIR=tests/fixtures/funnel).
