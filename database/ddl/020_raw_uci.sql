-- Raw UCI Online Retail II (independent domain; never joined to Olist). Verbatim text columns with
-- the exact source headers (incl. "Customer ID" with a space) + load metadata. Both yearly CSVs land
-- here; each file is replaced independently (by _source_file). _source_line_no = 1-based data-row
-- position in its file: the only stable line identifier (no natural line key exists).
create table if not exists raw.uci_online_retail_ii_lines (
    "Invoice" text not null,
    "StockCode" text not null,
    "Description" text,
    "Quantity" text,
    "InvoiceDate" text,
    "Price" text,
    "Customer ID" text,
    "Country" text,
    _source_line_no bigint not null,
    _ingested_at timestamptz not null default now(),
    _source_file text not null,
    _batch_id uuid not null,
    _row_hash char(64) not null,
    primary key (_source_file, _source_line_no)
);
create index if not exists ix_uci_online_retail_ii_lines__nk
    on raw.uci_online_retail_ii_lines ("Invoice", "StockCode");
