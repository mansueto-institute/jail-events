import numpy as np
from PIL import Image, ImageEnhance, ImageDraw
import os
from matplotlib import pyplot as plt
import polars as pl
import cv2


def resize_image(img:  Image.Image) -> Image.Image:
    """
    Crop and resize an image to size 3300 x 2550
    """
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.0)
    imgarr = np.array(img)
    y_df = pl.DataFrame(imgarr).select(
        pl.col("*") / 255
    ).select(
        pl.sum_horizontal(pl.col("*")).rolling_median(window_size=60, center=True, min_samples=1)
    ).with_row_index().drop_nulls().with_columns(
        pl.col("column_0") / img.width
    )
    x_df = pl.DataFrame(imgarr.transpose()).select(
        pl.col("*") / 255
    ).select(
        pl.sum_horizontal(pl.col("*")).rolling_median(window_size=50, center=True, min_samples=1)
    ).with_row_index().drop_nulls().with_columns(
        pl.col("column_0") / img.height
    )
    
    x_vals = x_df.with_columns(
        pl.when(pl.col("column_0") > (0.98 * (np.mean(imgarr) / 237)))
        .then(0.0).otherwise(pl.col("column_0")).alias("column_0")
    ).with_columns(
        pl.col("column_0").diff().alias("diff"),
        (pl.col("column_0").diff().abs() < 0.01).alias("is_flat"),
    ).filter(
        pl.col("is_flat") == False
    ).select(
        pl.col("index").min().alias("min_x"),
        pl.col("index").max().alias("max_x")
    ).to_dicts()[0]

    y_vals = y_df.with_columns(
        pl.when(pl.col("column_0") > (0.98 * (np.mean(imgarr) / 237)))
        .then(0.0).otherwise(pl.col("column_0")).alias("column_0")
    ).with_columns(
        pl.col("column_0").diff().alias("diff"),
        (pl.col("column_0").diff().abs() < 0.01).alias("is_flat"),
    ).filter(
        pl.col("is_flat") == False
    ).select(
        pl.col("index").min().alias("min_y"),
        pl.col("index").max().alias("max_y")
    ).to_dicts()[0]
    x_margin = img.height*0.01
    y_margin = img.width*0.01
    print(f"x_vals: {x_vals}, y_vals: {y_vals}")
    print(f"x_margin: {x_margin}, y_margin: {y_margin}")
    print(np.mean(imgarr))
    new_img = img.crop((x_vals["min_x"] - x_margin, y_vals["min_y"] - y_margin, x_vals["max_x"] + x_margin, y_vals["max_y"] + y_margin))
    new_img = new_img.resize((2550, 3300), Image.Resampling.LANCZOS)
    print(f"new_img size: {new_img.size}")
    return x_df, y_df, new_img