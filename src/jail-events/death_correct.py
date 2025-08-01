import polars as pl

file_path = "data/jails_pdfs_cleanned.parquet"

df = pl.read_parquet(file_path)

print(df.schema)
print("---")

df = df.with_columns(
    (
        (
            (
                pl.col("Deceased Name")
                .str.strip_chars()
                .str.replace_all("N?a?m?e? ?o?f? ?d?e?c?e?a?s?e?d ? ?:? ?", "")
                .str.strip_chars()
                .str.replace_all("^$", "N/A")
                == "N/A"
            ).cast(pl.Int8)
        )
        + (
            (
                pl.col("Deceased Cause")
                .str.strip_chars()
                .str.replace_all("S?p?e?c?i?f?i?c? ?c?a?u?s?e? ?o?f? ?d?e?a?t?h? ? ?:? ?", "")
                .str.strip_chars()
                .str.replace_all("^$", "N/A")
                == "N/A"
            ).cast(pl.Int8)
        )
        + (
            (
                pl.col("Deceased Date and Time")
                .str.strip_chars()
                .str.replace_all("D?a?t?e? ?\&? ?t?i?m?e? ?o?f? ?d?e?a?t?h? ? ?:? ?", "")
                .str.strip_chars()
                .str.replace_all("^$", "N/A")
                == "N/A"
            ).cast(pl.Int8)
        )
        + (
            (
                pl.col("Deceased on Suicide Watch")
                .str.strip_chars()
                .str.replace_all("No filled box found", "N/A")
                .str.strip_chars()
                .str.replace_all("^Y.*", "Yes")
                == "N/A"
            ).cast(pl.Int8)
        )
        + (
            (
                pl.col("Deceased Reporter")
                .str.strip_chars()
                .str.replace_all("R?e?p?o?r?t?e?d? ?b?y? ?:? ?", "")
                .str.strip_chars()
                .str.replace_all("^$", "N/A")
                == "N/A"
            ).cast(pl.Int8)
        )
    ).alias("Death_vote")
)

print(df.group_by(pl.col("Death_vote")).agg(pl.len()).sort("Death_vote"))
