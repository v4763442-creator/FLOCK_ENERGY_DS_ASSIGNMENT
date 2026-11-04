"""
I/O utilities for loading raw and cleaned REFIT data with strict memory management.
"""
import csv
from pathlib import Path
from typing import List
import pandas as pd
import numpy as np

from config import RAW_DTYPES, CLEAN_DTYPES, DATA_DIR, PROCESSED_DATA_DIR


def load_raw_house1(data_dir: Path = DATA_DIR, nrows: int = None) -> pd.DataFrame:
    """
    Loads RAW House 1 (Part 1 and Part 2) as a single logical series.
    Resolves the 95-day overlap by taking Part 1 up to 2014-10-01 01:27:07
    and Part 2 thereafter.
    """
    p1_path = data_dir / "RAW_House1_Part1.csv"
    p2_path = data_dir / "RAW_House1_Part2.csv"
    
    if not p1_path.exists() or not p2_path.exists():
        raise FileNotFoundError(f"RAW House 1 files not found in {data_dir}")
        
    df1 = pd.read_csv(p1_path, dtype=RAW_DTYPES, nrows=nrows)
    p1_end_time = "2014-10-01 01:27:07"
    df1 = df1[df1['Time'] <= p1_end_time].copy()
    
    if nrows is None:
        df2 = pd.read_csv(p2_path, dtype=RAW_DTYPES)
        df2 = df2[df2['Time'] > p1_end_time].copy()
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


def cache_clean_house_1min(house_id: int, data_dir: Path = DATA_DIR) -> Path:
    """
    Streams official CLEAN_House{N}.csv line by line to a 1-minute Parquet cache.
    Guarantees zero memory strain on constrained systems.
    """
    out_path = PROCESSED_DATA_DIR / f"clean_house{house_id}_1min.parquet"
    if out_path.exists():
        return out_path
        
    csv_path = data_dir / f"CLEAN_House{house_id}.csv"
    channels = ['Aggregate'] + [f'Appliance{i}' for i in range(1, 10)] + ['Issues']
    current_minute = None
    cur_sum = [0.0] * 11
    cur_count = [0] * 11
    records = []
    
    with open(csv_path, 'r', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        col_indices = [header.index(c) for c in channels]
        unix_idx = header.index('Unix')
        
        for row in reader:
            unix_utc = int(row[unix_idx])
            minute_epoch = (unix_utc // 60) * 60
            
            if current_minute is None:
                current_minute = minute_epoch
                
            if minute_epoch != current_minute:
                row_out = [current_minute]
                for c_idx in range(11):
                    if cur_count[c_idx] > 0:
                        if c_idx == 10:  # Issues
                            row_out.append(int(cur_sum[c_idx] > 0))
                        else:
                            row_out.append(cur_sum[c_idx] / cur_count[c_idx])
                    else:
                        row_out.append(np.nan)
                records.append(row_out)
                current_minute = minute_epoch
                cur_sum = [0.0] * 11
                cur_count = [0] * 11
                
            for c_idx in range(11):
                raw_v = row[col_indices[c_idx]]
                if raw_v != '' and raw_v != 'NaN' and raw_v != 'nan':
                    v = float(raw_v)
                    if c_idx == 10:
                        cur_sum[c_idx] = max(cur_sum[c_idx], v)
                        cur_count[c_idx] += 1
                    else:
                        cur_sum[c_idx] += v
                        cur_count[c_idx] += 1

    if current_minute is not None:
        row_out = [current_minute]
        for c_idx in range(11):
            if cur_count[c_idx] > 0:
                if c_idx == 10:
                    row_out.append(int(cur_sum[c_idx] > 0))
                else:
                    row_out.append(cur_sum[c_idx] / cur_count[c_idx])
            else:
                row_out.append(np.nan)
        records.append(row_out)
        
    cols = ['minute_utc'] + channels
    df_1min = pd.DataFrame(records, columns=cols)
    df_1min['dt_utc'] = pd.to_datetime(df_1min['minute_utc'], unit='s', utc=True)
    df_1min = df_1min.set_index('dt_utc').drop(columns=['minute_utc'])
    df_1min = df_1min.groupby(level=0).mean()
    
    full_idx = pd.date_range(start=df_1min.index.min(), end=df_1min.index.max(), freq='1min', tz='UTC')
    df_1min = df_1min.reindex(full_idx)
    df_1min.to_parquet(out_path)
    return out_path
