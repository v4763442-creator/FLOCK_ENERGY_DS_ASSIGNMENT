"""
Script to cache official cleaned houses 1 to 5 at 1-minute resolution
using line-by-line streaming (zero memory overhead).
"""
import csv
from pathlib import Path
import pandas as pd
import numpy as np
from config import DATA_DIR, PROCESSED_DATA_DIR, WM_COLUMNS

def cache_clean_house_1min(house_id: int, data_dir: Path = DATA_DIR) -> Path:
    out_path = PROCESSED_DATA_DIR / f"clean_house{house_id}_1min.parquet"
    if out_path.exists():
        print(f"House {house_id} 1-min cached file already exists: {out_path.name}")
        return out_path
        
    csv_path = data_dir / f"CLEAN_House{house_id}.csv"
    print(f"Streaming {csv_path.name} to 1-minute resolution...")
    
    channels = ['Aggregate'] + [f'Appliance{i}' for i in range(1, 10)] + ['Issues']
    current_minute = None
    cur_sum = [0.0] * 11
    cur_count = [0] * 11
    records = []
    
    with open(csv_path, 'r', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        # Find column indices
        col_indices = [header.index(c) for c in channels]
        unix_idx = header.index('Unix')
        
        for row in reader:
            unix_utc = int(row[unix_idx])
            minute_epoch = (unix_utc // 60) * 60
            
            if current_minute is None:
                current_minute = minute_epoch
                
            if minute_epoch != current_minute:
                # Emit
                row_out = [current_minute]
                for c_idx in range(11):
                    if cur_count[c_idx] > 0:
                        # For Issues, take max (if any issue in minute, minute is flagged)
                        if c_idx == 10:
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
                    if c_idx == 10:  # Issues
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
    
    # Reindex on full continuous grid
    full_idx = pd.date_range(start=df_1min.index.min(), end=df_1min.index.max(), freq='1min', tz='UTC')
    df_1min = df_1min.reindex(full_idx)
    
    df_1min.to_parquet(out_path)
    print(f"Successfully cached {len(df_1min):,} 1-minute rows to {out_path.name}")
    return out_path

if __name__ == "__main__":
    for h in [1, 2, 3, 4, 5]:
        cache_clean_house_1min(h)
