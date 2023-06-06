import streamlit as st
from pymongo import MongoClient
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import datetime
import numpy as np
from utils import *
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.sidebar.header("Dashboard `version 2`")

# ... rest of your sidebar settings ...

# Connect to MongoDB
MONGO_URL = st.secrets["MONGO_URL"]
client = MongoClient(MONGO_URL)
db = client.BettingData
trades = db.Trades
historic_data = db.HistoricData
## Fetch data from MongoDB
trades = trades.find()
trades = pd.DataFrame(list(trades))
historic_data = historic_data.find()
historic_data = pd.DataFrame(list(historic_data))

selected_page = st.sidebar.selectbox("Select Page", ["Home", "Backtest", "Specific Account"])

## HOME PAGE - overview of total profit/loss and cumulative return
if selected_page == "Home":
    # Total profit loss graph
    # Filter out null bsp and zero bsp
    # Ensure the columns are numeric and replace any infinities or NaNs with 0
    trades["stake_size"] = pd.to_numeric(trades["stake_size"], errors='coerce').replace([np.inf, -np.inf], np.nan).fillna(0)
    trades["win_odds"] = pd.to_numeric(trades["win_odds"], errors='coerce').replace([np.inf, -np.inf], np.nan).fillna(0)
    trades["bsp"] = pd.to_numeric(trades["bsp"], errors='coerce').replace([np.inf, -np.inf], np.nan).fillna(0)
    trades["return"] = pd.to_numeric(trades["return"], errors='coerce').replace([np.inf, -np.inf], np.nan).fillna(0)

    trades = trades[(trades["bsp"].notnull()) | (trades["bsp"] != 0)]
    figure, trades = plot_total_profit_loss(trades)
    st.pyplot(figure)

## Backtesting Page - Test the model on historical data
elif selected_page == "Backtest":
    col1 = st.columns(1)
    col1.header("Backtest")
else: 
    usernames, bookies = get_usernames_and_bookies(trades)
    selected_bookie = st.sidebar.selectbox("Select Bookie", bookies)
    selected_username = st.sidebar.selectbox("Select Username", usernames)
    trades_p, trades_np = fetch_data(trades, selected_bookie, selected_username)


## Look at Specific Accounts