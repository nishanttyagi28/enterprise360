"""Contracts for the 9 files of Kaggle ``olistbr/brazilian-ecommerce`` (headers verified on file)."""

from __future__ import annotations

from ingestion.sources.contracts import SourceContract

OLIST_CONTRACTS: tuple[SourceContract, ...] = (
    SourceContract(
        name="olist_customers",
        file_name="olist_customers_dataset.csv",
        table="olist_customers",
        columns=(
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ),
        natural_key=("customer_id",),
    ),
    SourceContract(
        name="olist_geolocation",
        file_name="olist_geolocation_dataset.csv",
        table="olist_geolocation",
        columns=(
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_city",
            "geolocation_state",
        ),
        # No natural key: many (even identical) points per zip prefix. Deduped in dbt.
        natural_key=("geolocation_zip_code_prefix",),
    ),
    SourceContract(
        name="olist_order_items",
        file_name="olist_order_items_dataset.csv",
        table="olist_order_items",
        columns=(
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ),
        natural_key=("order_id", "order_item_id"),
    ),
    SourceContract(
        name="olist_order_payments",
        file_name="olist_order_payments_dataset.csv",
        table="olist_order_payments",
        columns=(
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ),
        natural_key=("order_id", "payment_sequential"),
    ),
    SourceContract(
        name="olist_order_reviews",
        file_name="olist_order_reviews_dataset.csv",
        table="olist_order_reviews",
        columns=(
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ),
        # review_id alone is NOT unique in the source (same review attached to several orders).
        natural_key=("review_id", "order_id"),
    ),
    SourceContract(
        name="olist_orders",
        file_name="olist_orders_dataset.csv",
        table="olist_orders",
        columns=(
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ),
        natural_key=("order_id",),
    ),
    SourceContract(
        name="olist_products",
        file_name="olist_products_dataset.csv",
        table="olist_products",
        columns=(
            "product_id",
            "product_category_name",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ),
        natural_key=("product_id",),
    ),
    SourceContract(
        name="olist_sellers",
        file_name="olist_sellers_dataset.csv",
        table="olist_sellers",
        columns=("seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"),
        natural_key=("seller_id",),
    ),
    SourceContract(
        name="olist_category_translation",
        file_name="product_category_name_translation.csv",
        table="olist_product_category_name_translation",
        columns=("product_category_name", "product_category_name_english"),
        natural_key=("product_category_name",),
    ),
)

_BY_NAME = {c.name: c for c in OLIST_CONTRACTS}


def get_contract(name: str) -> SourceContract:
    try:
        return _BY_NAME[name]
    except KeyError:
        raise KeyError(f"unknown source {name!r}; known: {sorted(_BY_NAME)}") from None
