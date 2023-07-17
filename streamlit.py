import streamlit as st
from pymongo import MongoClient
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import datetime
import numpy as np
from utils import *

from datetime import datetime, timedelta

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.sidebar.header("Dashboard `version 2`")

# ... rest of your sidebar settings ...

# Connect to MongoDB
MONGO_URL = st.secrets["MONGO_URL"]
# client = MongoClient(MONGO_URL)
# db = client.BettingData
# trades = db.Trades
# historic_data = db.HistoricData
## Fetch data from MongoDB
# trades = trades.find()
# trades = pd.DataFrame(list(trades))
# historic_data = historic_data.find()
# historic_data = pd.DataFrame(list(historic_data))

# Initialize connection.
# Uses st.cache_resource to only run once.
@st.cache_resource
def init_connection():
    return MongoClient(MONGO_URL)


client = init_connection()

projection = {
    "win_odds": 1,
    "balance": 1,
    "stake_size": 1,
    "best_lay_price": 1,
    "return": 1,
    "timestamp": 1,
}

# Pull data from the collection.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
@st.cache_data(ttl=600)
def get_data():
    db = client.BettingData
    trades = db.Trades
    trades = trades.find()
    trades = pd.DataFrame(list(trades))  # make hashable for st.cache_data
    return trades


trades = get_data()

selected_page = st.sidebar.selectbox(
    "Select Page", ["Home", "Backtest", "Specific Account"]
)


@st.cache(ttl=600)
def get_active_accounts():
    # Get current time and time 24 hours ago
    now = datetime.now()
    one_day_ago = now - timedelta(days=1)

    # Fetch trades from the past 24 hours
    db = client.BettingData
    trades = db.Trades
    recent_trades = trades.find()
    recent_trades = pd.DataFrame(list(recent_trades))

    # Convert Unix timestamp to datetime
    recent_trades["timestamp"] = pd.to_datetime(recent_trades["timestamp"], unit="s")

    # Filter out trades from the past 24 hours
    recent_trades = recent_trades[recent_trades["timestamp"] >= one_day_ago]

    # Group trades by account and calculate statistics
    active_accounts = (
        recent_trades.groupby(["username", "bookie"])
        .agg(
            {
                "balance": "last",  # Balance after last trade
                "timestamp": "count",  # Number of trades
                "timestamp": lambda x: (now - x.max()).total_seconds() / 3600,
            }
        )  # Time since last trade in hours
        .rename(
            columns={"timestamp": "num_trades", "timestamp": "hours_since_last_trade"}
        )
    )

    return active_accounts


## HOME PAGE - overview of total profit/loss and cumulative return
if selected_page == "Home":
    # Total profit loss graph
    # Filter out null bsp and zero bsp
    # Ensure the columns are numeric and replace any infinities or NaNs with 0
    trades["stake_size"] = pd.to_numeric(trades["stake_size"])
    trades["win_odds"] = pd.to_numeric(trades["win_odds"])
    # trades["bsp"] = pd.to_numeric(trades["bsp"])

    trades_p, trades_np = prepare_data(trades)
    trades_p = trades_p[(trades_p["bsp"] != 0.0) & (trades_p["bsp"].notnull())]
    trades_p["return"] = pd.to_numeric(trades_p["return"])
    figure, trades = plot_total_profit_loss(trades_p)
    st.pyplot(figure)

    col1, col2 = st.columns(2)
    col1.metric("Total Turnover", trades["stake_size"].sum())
    col2.metric("Bets Placed", len(trades_p))

    # Fetch active accounts and display bar chart
    active_accounts = get_active_accounts()
    st.bar_chart(active_accounts)

## Backtesting Page - Test the model on historical data


elif selected_page == "Backtest":
    st.header("Backtest")
    # Define a default function to be shown to the user
    default_function = """
    def user_function():
        # Write your function logic here
        st.write("This is a user-defined function.")
    """

    with st.form(key="backtest_form"):
        user_code = st.text_area("Define your function here:", value=default_function)
        submit_button = st.form_submit_button(label="Start Backtest")

    if submit_button:
        # Execute the user-defined code
        exec(user_code, globals())

        # Call the user-defined function in the backtest
        def backtest(user_function):
            # Here we assume the user has defined a function called 'user_function'
            user_function()

        backtest(user_function)

        # Insert code to produce plots and metrics after the backtest
        # For now, let's just print a success message
        st.write("Backtest complete, producing plots and metrics.")


else:
    # Get all the bookies excluding None entries
    bookies = trades[trades["bookie"].notnull()]["bookie"].unique().tolist()
    bookies.append("All")

    selected_bookie = st.sidebar.selectbox("Select Bookie", bookies)

    if selected_bookie != "All":
        usernames = (
            trades[trades["bookie"] == selected_bookie]["username"].unique().tolist()
        )
    else:
        usernames = trades["username"].unique().tolist()
    usernames.append("All")

    selected_username = st.sidebar.selectbox("Select Username", usernames)

    trades_p, trades_np = fetch_data(trades, selected_bookie, selected_username)
    # Balance Histogram of EV and 10 Most Recent Trades
    col1, col2, col3 = st.columns(3)
    col1.header(f"Balance for {selected_bookie} - {selected_username}")

    figure = plot_balance(trades_p)

    col1.pyplot(figure)

    # Histogram of EV
    col2.header(f"EV for {selected_bookie} - {selected_username}")
    placed_evs = trades_p[(trades_p["bsp"] != 0.0) & (trades_p["bsp"].notnull())]
    np_evs = trades_np[(trades_np["bsp"] != 0.0) & (trades_np["bsp"].notnull())]

    placed_evs = calculate_ev(placed_evs)
    np_evs = calculate_ev(np_evs)

    # plot with seaborn distplot
    figure = plt.figure(figsize=(10, 5))
    sns.distplot(placed_evs["ev"], label="placed")
    sns.distplot(np_evs["ev"], label="not placed")
    plt.legend()
    col2.pyplot(figure)

    # 10 Most Recent Trades
    col3.header(f"10 Most Recent Trades for {selected_bookie} - {selected_username}")
    recent = trades_p.tail(10)
    col3.table(recent[["win_odds", "best_lay_price", "balance", "stake_size"]])

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mean EV", round(placed_evs["ev"].mean(), 4))
    col2.metric("Bets Placed", len(trades_p))
    col3.metric("Mean BSP", round(placed_evs["bsp"].mean(), 4))
    col4.metric("Mean EV (not placed)", round(np_evs["ev"].mean(), 4))
## Look at Specific Accounts
