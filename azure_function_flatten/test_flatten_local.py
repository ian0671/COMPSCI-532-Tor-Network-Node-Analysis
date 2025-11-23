"""Quick local validation of flatten + sanitize logic.
Run: python azure_function_flatten/test_flatten_local.py
Creates sample_input.parquet then processes it like the blob trigger and
writes sample_flat.parquet. Prints head + dtypes.
"""
import pandas as pd
from pathlib import Path
import sys, os, json

# Ensure project root is on path for direct execution
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from azure_function_flatten.flatten_blob_trigger.__init__ import flatten_df, sanitize_for_parquet

def make_sample(path: str):
    df = pd.DataFrame({
        'ip': ['1.1.1.1', '8.8.8.8'],
        'scores': [
            {'threat': 5, 'confidence': 0.8},
            {'threat': 1, 'confidence': 0.2},
        ],
        'tags': [
            ['ddos', 'botnet'],
            ['resolver'],
        ],
        'mixed': [
            {'a': 1},
            ['list', 'form'],
        ],
    })
    # Pre-serialize columns that have heterogeneous complex types to ensure initial Parquet write succeeds
    df['mixed'] = df['mixed'].apply(json.dumps)
    df.to_parquet(path, index=False)
    return path

def process(in_path: str, out_path: str):
    df = pd.read_parquet(in_path)
    flat = flatten_df(df)
    flat = sanitize_for_parquet(flat)
    flat.to_parquet(out_path, index=False, engine='pyarrow')
    return flat

if __name__ == '__main__':
    inp = make_sample('sample_input.parquet')
    out = 'sample_flat.parquet'
    flat = process(inp, out)
    print(flat.head())
    print('\nDtypes:', flat.dtypes)
    print(f'Wrote {out}')
