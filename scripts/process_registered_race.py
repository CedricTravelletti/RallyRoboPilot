""" Process data from a registered race. 

This scipt automatically splits the data in laps. 

"""
import os 
import numpy as np 
import pandas as pd


def load_data(file_path):
    df = pd.read_pickle(file_path)
    return df

def split_laps(df):
    df['lap_time_diff'] = df['last_lap_duration'].diff().abs()

    threshold = 1e-4
    split_indices = df.index[df['lap_time_diff'] > threshold].tolist()

    split_dataframes = []

    start_idx = 0
    for idx in split_indices:
        split_dataframes.append(df.iloc[start_idx:idx].drop(columns=['lap_time_diff']))
        start_idx = idx

    split_dataframes.append(df.iloc[start_idx:].drop(columns=['lap_time_diff']))

    # Compute total time of each lap.
    for split_df in split_dataframes:
        total_time = split_df['absolute_time'].iloc[-1] - split_df['absolute_time'].iloc[0]
        split_df['current_lap_total_time'] = total_time
# Throw away first and last lap (since those are not full laps).
return split_dataframes[1:-1]
