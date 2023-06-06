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
    trades["stake_size"] = pd.to_numeric(trades["stake_size"])
    trades["win_odds"] = pd.to_numeric(trades["win_odds"])
    # trades["bsp"] = pd.to_numeric(trades["bsp"])
    trades["return"] = pd.to_numeric(trades["return"])
    
    trades_p, trades_np = prepare_data(trades)
    trades_p = trades_p[(trades_p["bsp"]!= 0.0) & (trades_p["bsp"].notnull())]
    figure, trades = plot_total_profit_loss(trades_p)
    st.pyplot(figure)

## Backtesting Page - Test the model on historical data
elif selected_page == "Backtest":
    col1 = st.columns(1)
    col1.header("Backtest")
else: 
    # Get all the bookies excluding None entries
    bookies = trades[trades["bookie"].notnull()]["bookie"].unique().tolist()
    bookies.append("All")

    selected_bookie = st.sidebar.selectbox("Select Bookie", bookies)
    
    if selected_bookie != "All":
        usernames = trades[trades["bookie"] == selected_bookie]["username"].unique().tolist()
    else:
        usernames = trades["username"].unique().tolist()
    usernames.append("All")

    selected_username = st.sidebar.selectbox("Select Username", usernames)

    trades_p, trades_np = fetch_data(trades, selected_bookie, selected_username)
    trades_p = trades_p[(trades_p["bsp"]!= 0.0) & (trades_p["bsp"].notnull())]
    trades_np = trades_np[(trades_np["bsp"]!= 0.0) & (trades_np["bsp"].notnull())]

    # Balance Histogram of EV and 10 Most Recent Trades
    col1, col2, col3 = st.columns(3)
    col1.header(f"Balance for {selected_bookie} - {selected_username}")

    figure = plot_balance(trades_p)
    col1.pyplot(figure)

    # Histogram of EV
    col2.header(f"EV for {selected_bookie} - {selected_username}")
    trades_p = calculate_ev(trades_p)
    trades_np = calculate_ev(trades_np)

    # plot with seaborn distplot
    figure = plt.figure(figsize=(10, 5))
    sns.distplot(trades_p["ev"], label="placed")
    sns.distplot(trades_np["ev"], label="not placed")
    plt.legend()
    col2.pyplot(figure)

    # 10 Most Recent Trades
    col3.header(f"10 Most Recent Trades for {selected_bookie} - {selected_username}")
    recent = trades_p.tail(10)
    col3.table(recent[["win_odds", "best_lay_price", "balance", "stake_size"]])



## Look at Specific Accounts