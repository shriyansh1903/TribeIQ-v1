import pandas as pd
from typing import List, Any, Optional

def safe_get_column(df: pd.DataFrame, alternatives: List[str], default: Optional[str] = None) -> Optional[str]:
    """
    Search for a matching column name in the dataframe (case-insensitive and whitespace-stripped).
    """
    if df is None or df.empty:
        return default
    
    col_map = {c.strip().lower(): c for c in df.columns}
    
    for alt in alternatives:
        alt_clean = alt.strip().lower()
        if alt_clean in col_map:
            return col_map[alt_clean]
            
    return default

def safe_column_exists(df: pd.DataFrame, col_name: str) -> bool:
    if df is None or df.empty:
        return False
    return col_name in df.columns or col_name.strip().lower() in [c.strip().lower() for c in df.columns]

def safe_status_column(df: pd.DataFrame) -> Optional[str]:
    return safe_get_column(df, ["Status", "status", "Vendor Status", "Active / Inactive Status", "Procurement Status"])

def safe_numeric_column(df: pd.DataFrame, col_name: str, errors: str = 'coerce') -> pd.Series:
    actual_col = safe_get_column(df, [col_name])
    if actual_col and actual_col in df.columns:
        return pd.to_numeric(df[actual_col], errors=errors)
    return pd.Series(dtype='float64')

def safe_date_column(df: pd.DataFrame, col_name: str) -> pd.Series:
    actual_col = safe_get_column(df, [col_name])
    if actual_col and actual_col in df.columns:
        return pd.to_datetime(df[actual_col], errors='coerce')
    return pd.Series(dtype='datetime64[ns]')
