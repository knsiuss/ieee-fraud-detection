## conver all files to parquet
import pandas as pd
import numpy as np
import time 
import os

def reduce_mem_usage(df, verbose=True):
    """Reduce memory usage by optimizing dtypes"""
    start_mem = df.memory_usage().sum() / 1024**2

    for col in df.columns:
        col_type = df[col].dtype

        if col_type != object:
            c_min = df[col].min()
            c_max = df[col].max()

            if str(col_type)[:3] == 'int':
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
                else:
                    df[col] = df[col].astype(np.int64)
            else:
                if c_min > np.finfo(np.float16).min and c_max < np.finfo(np.float16).max:
                    df[col] = df[col].astype(np.float32)
                elif c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                    df[col] = df[col].astype(np.float32)
                else:
                    df[col] = df[col].astype(np.float64)
        else:
            df[col] = df[col].astype('category')
    
    end_mem = df.memory_usage().sum() / 1024**2

    if verbose:
        reduction = 100 * (start_mem - end_mem) / start_mem
        print(f"    Memory : {start_mem:1f}MB -> {end_mem:.1f}MB {reduction:.1f}%")

    return df

## data preperation 

csv_to_parquet = {
    'train_transaction' : 'dataset/train_transaction.csv',
    'train_identity' : 'dataset/train_identity.csv',
    'test_transaction' : 'dataset/test_transaction.csv',
    'test_identity' : 'dataset/test_identity.csv',
    'sample_submission' : 'dataset/sample_submission.csv' 
}

total_start = time.time()
result = []

for name, csv_path in csv_to_parquet.items():
    print(name)

    if not os.path.exists(csv_path):
        print("FILE NOT FOUND ")
        continue

    try:
        # load
        print("load csv")
        start = time.time()
        df = pd.read_csv(csv_path)
        load_time = time.time() - start
        csv_size = os.path.getsize(csv_path) / (1024**2)

        print(f"    {load_time:.1f}s | {df.shape[0]:,} rows x {df.shape[1]} cols ")
        print(f"    CSV  : {csv_size:.1f}MB")

        # SKIP SAMPLE SUBMISSION
        if name != 'sample_submission':
            df = reduce_mem_usage(df, verbose=True)
        
        # save to parquet
        print("saving")
        start = time.time()
        parquet_path = csv_path.replace('.csv', '.parquet')
        df.to_parquet(parquet_path, engine='pyarrow', compression='snappy')
        save_time = time.time() - start
        parquet_size = os.path.getsize(parquet_path) / (1024**2)

        print(f"      {save_time:.1f}s | Parquet: {parquet_size:.1f} MB")
        print(f"      Saved {(csv_size - parquet_size):.1f} MB ({(1-parquet_size/csv_size)*100:.0f}%)")

        result.append({
            'File' : name,
            'Rows' : f"{df.shape[0]}",
            'Cols' : df.shape[1],
            'CSV_MB' : csv_size,
            'Parquet_MB' : parquet_size,
            'Saved_MB' : csv_size - parquet_size,
            'Compression_%' : (1- parquet_size/csv_size) * 100

        })
        
        del df
    except Exception as e:
        print(f'error {e}')
