"""Contract for UCI Online Retail II (UCI ML Repository id 502), exported to CSV per year sheet.

Independent source: it never joins Olist objects. Both files land in ONE raw table; each file is
replaced independently (ReplaceScope.FILE). There is no natural line key (the same StockCode can
appear on several lines of one invoice), so the file row position is recorded as _source_line_no.
"""

from __future__ import annotations

from ingestion.sources.contracts import ReplaceScope, SourceContract

UCI_ONLINE_RETAIL_II = SourceContract(
    name="uci_online_retail_ii",
    file_name="online_retail_II_Year_2009-2010.csv",
    extra_file_names=("online_retail_II_Year_2010-2011.csv",),
    table="uci_online_retail_ii_lines",
    columns=(
        "Invoice",
        "StockCode",
        "Description",
        "Quantity",
        "InvoiceDate",
        "Price",
        "Customer ID",
        "Country",
    ),
    natural_key=("Invoice", "StockCode"),  # index only; NOT unique
    replace_scope=ReplaceScope.FILE,
    track_line_numbers=True,
)

UCI_CONTRACTS: tuple[SourceContract, ...] = (UCI_ONLINE_RETAIL_II,)
