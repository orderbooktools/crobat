import pandas as pd

df = pd.read_excel('L2_orderbook_events_ask2021-06-29 21:11:00.721488.xlsx')
pd.set_option("display.max_columns", 101)
print(df.head())