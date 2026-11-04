"""
I/O utilities for loading raw and cleaned REFIT data with strict memory management.
"""
from pathlib import Path
import pandas as pd
import numpy as np
from config import RAW_DTYPES, CLEAN_DTYPES, DATA_DIR


def load_raw_house1(data_dir: Path = DATA_DIR, nrows: int = None) -> pd.DataFrame:
    """
    Loads RAW House 1 (Part 1 and Part 2) as a single logical series.
    Resolves the 95-day overlap (2014-06-27 to 2014-10-01) by taking Part 1
    up to 2014-10-01 01:27:07 and Part 2 thereafter, matching the official
    dataset transition boundary.
    """
    p1_path = data_dir / "RAW_House1_Part1.csv"
    p2_path = data_dir / "RAW_House1_Part2.csv"
    
    if not p1_path.exists() or not p2_path.exists():
        raise FileNotFoundError(f"RAW House 1 files not found in {data_dir}")
        
    print(f"Loading {p1_path.name}...")
    df1 = pd.read_csv(p1_path, dtype=RAW_DTYPES, nrows=nrows)
    
    # Boundary timestamp where Part 1 ends: 2014-10-01 01:27:07
    p1_end_time = "2014-10-01 01:27:07"
    df1 = df1[df1['Time'] <= p1_end_time].copy()
    
    if nrows is None:
        print(f"Loading {p2_path.name}...")
        df2 = pd.read_csv(p2_path, dtype=RAW_DTYPES)
        df2 = df2[df2['Time'] > p1_end_time].copy()
        print(f"Merging Part 1 ({len(df1):,} rows) and Part 2 ({len(df2):,} rows)...")
        df = pd.concat([df1, df2], ignore_index=True)
        del df1, df2
    else:
        df = df1
        
    return df


def load_clean_house(house_id: int, data_dir: Path = DATA_DIR, usecols: list = None, nrows: int = None) -> pd.DataFrame:
    """
    Loads official cleaned REFIT data for a given house.
    """
    clean_path = data_dir / f"CLEAN_House{house_id}.csv"
    if not clean_path.exists():
        raise FileNotFoundError(f"Clean file not found: {clean_path}")
        
    dtypes = CLEAN_DTYPES
    if usecols is not None:
        dtypes = {k: v for k, v in CLEAN_DTYPES.items() if k in usecols}
        
    df = pd.read_csv(clean_path, usecols=usecols, dtype=dtypes, nrows=nrows)
    return df
