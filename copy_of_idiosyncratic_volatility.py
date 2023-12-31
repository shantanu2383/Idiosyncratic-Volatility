# -*- coding: utf-8 -*-
"""Copy of Idiosyncratic Volatility.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1SkazmhYAuiye21rf0az8BtuG9snm_gfV
"""

#Import Libraries
import pandas as pd
import statsmodels.formula.api as smf
import numpy as np
import matplotlib.pyplot as plt

!pip install pandasql
import os
from datetime import datetime
from sklearn.model_selection import train_test_split
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.arima_model import ARIMA
from sklearn.metrics import mean_squared_error, mean_absolute_error

import math
import matplotlib.pyplot as plt
from datetime import datetime
import seaborn as sns
import pandasql as ps
from sqlite3 import connect
from google.colab import drive
drive.mount("/content/gdrive", force_remount=True)

conn=connect(':memory:')

file="DailyStockPrice.csv"


price_df=pd.read_csv(raw + file)
# Parse the 'date' column to a datetime format
price_df['date'] = pd.to_datetime(price_df['date'], format='%Y-%m-%d')

# Filter to only keep data from 2018 onwards
price_df = price_df[(price_df['date'] >= "2015-01-01")]

# Parse Relevant Variables, only keep distinct rows
price_df = price_df[['ticker', 'date', 'adj_close', 'adj_volume']].drop_duplicates()
print(price_df)

price_df=price_df[price_df['adj_close']>5]

print(price_df)

file= "ZACKS_MT_2.csv"

# Read the CSV file into a DataFrame 'map'
map = pd.read_csv(aux + file)



# Keep distinct rows based on 'ticker', 'exchange', 'asset_type', 'comp_type'
map = map[['ticker', 'exchange', 'asset_type', 'comp_type']].drop_duplicates()

# Merge 'price_df' and 'map' DataFrames on the 'ticker' column
price_df_xmap = pd.merge(price_df, map, on='ticker', how='left')

# Convert to string type for filtering
price_df_xmap['exchange'] = price_df_xmap['exchange'].astype(str)
price_df_xmap['asset_type'] = price_df_xmap['asset_type'].astype(str)
price_df_xmap['comp_type'] = price_df_xmap['comp_type'].astype(str)

# Keep only rows where 'exchange' is either 'NYSE', 'AMEX', or 'NASDAQ'
relevant_exchanges = ['NYSE']
price_df_xmap = price_df_xmap[price_df_xmap['exchange'].isin(relevant_exchanges)]

# Keep only US Based common stocks where 'asset_type' is 'COM'
#price_df_xmap = price_df_xmap[price_df_xmap['asset_type'] == 'COM']

# Keep only industrial stocks where 'comp_type' is '1.0'
#price_df_xmap = price_df_xmap[price_df_xmap['comp_type'] == '1.0']

price_df = price_df_xmap

# Sort by 'ticker' and 'date', so stocks are listed consecutively
price_df = price_df.sort_values(['ticker', 'date'], ascending=True)

# Create a 'stock checker' column, shifted by one for previous day's ticker
#price_df['stock checker'] = price_df['ticker'].shift(1)

# Only keep rows where 'ticker' matches 'stock checker', i.e., we have prior day data for the same stock
#price_df = price_df[price_df['ticker'] == price_df['stock checker']]

# Calculate the 'daily_return' column
price_df['adj_close'] = pd.to_numeric(price_df['adj_close'], errors='coerce')
price_df['adj_close_prev_day'] = price_df.groupby('ticker')['adj_close'].shift(1)
price_df['daily_return'] = ((price_df['adj_close'] - price_df['adj_close_prev_day']) / price_df['adj_close_prev_day']) * 100

# Parse relevant variables and remove duplicates
price_df = price_df[['ticker', 'date', 'adj_close', 'daily_return', 'exchange']].drop_duplicates()

"""Import Fama French Factors"""

import pandas_datareader.data as web
from pandas_datareader.famafrench import get_available_datasets
datasets = get_available_datasets()



df_3_factor=[dataset for dataset in datasets if 'Research' in dataset and 'Factor' in dataset]
df_3_factor
ff=web.DataReader(df_3_factor[4],'famafrench',start='2015-01-01',end='2022-12-01')[0]
ff.reset_index(inplace=True)
ff

ff.rename(columns={'Date':'date'}, inplace=True)
ff['date']=pd.to_datetime(ff['date'])

merged_df = price_df.merge(ff, on='date', how='left')

main="/content/gdrive/MyDrive/"

g=pd.read_csv(main + "idiosyncratic_volatility.csv")
g

iv['residual_std_dev'].isnull().sum()

main=merged_df
main['year']=main['date'].dt.year

iv=main[['year', 'ticker']].drop_duplicates()
iv



iv = iv[(iv['year'] > 2016) & (iv['year'] < 2023)]

iv

# Convert the ticker columns to sets
set_g = set(g['ticker'])
set_iv = set(iv['ticker'])

# Calculate the intersections and differences
both = set_g.intersection(set_iv)
in_g_not_in_iv = set_g.difference(set_iv)
in_iv_not_in_g = set_iv.difference(set_g)

# Print the results
print(f"Tickers in both dataframes: {len(both)}")
print(f"Tickers in g but not in iv: {len(in_g_not_in_iv)}")
print(f"Tickers in iv but not in g: {len(in_iv_not_in_g)}")

import statsmodels.api as sm
iv = iv.reset_index(drop=True)


for index, row in iv.iterrows():
  temp = main[(main['ticker'] == row['ticker']) & (main['year'] == row['year'])]
  temp.dropna(inplace=True)
  if temp.empty:
    continue

  # define the dependent variable
  Y = temp['daily_return']

  # define the independent variables
  X = temp[['Mkt-RF', 'SMB', 'HML']]

  # add a constant to the independent variables matrix
  X = sm.add_constant(X)

  # conduct regression
  model = sm.OLS(Y, X, missing='drop')
  results = model.fit()

  try:
    # Get the coefficients from the fitted model
    beta_Mkt_RF = results.params.get('Mkt-RF', 0)
    beta_SMB = results.params.get('SMB', 0)
    beta_HML = results.params.get('HML', 0)
    intercept = results.params.get('const', 0)

    # Calculate the expected return for each observation
    temp['expected_return'] = intercept + beta_Mkt_RF*temp['Mkt-RF'] + beta_SMB*temp['SMB'] + beta_HML*temp['HML']

    # Calculate the residuals for each observation
    temp['residual'] = temp['daily_return'] - temp['expected_return']

    iv.loc[index, 'residual_std_dev'] = temp['residual'].std()

    print(f'Processed {index+1} of {len(iv)} rows: ticker={row["ticker"]}, year={row["year"]}')
  except Exception as e:
    print(f"Error occurred at index {index}: {e}")

iv

main="/content/gdrive/MyDrive/"

iv.to_csv(main + "idiosyncratic_volatility.csv")