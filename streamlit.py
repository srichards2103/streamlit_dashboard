import streamlit as st
from pymongo import MongoClient
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import datetime

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.sidebar.header("Dashboard `version 2`")


# ... rest of your sidebar settings ...

# Connect to MongoDB
MONGO_URL = st.secrets["MONGO_URL"]
client = MongoClient(MONGO_URL)
db = client.BettingData
collection = db.Trades

## Fetch data from MongoDB
data = collection.find()
data = pd.DataFrame(list(data))

# Get unique bookies from MongoDB
bookies = data['bookie'].unique()

# Add a dropdown menu for selecting a bookie
selected_bookie = st.sidebar.selectbox("Select Bookie", bookies)

# Filter your data based on the selected bookie
data_bookie = data[data['bookie'] == selected_bookie]

# Get unique usernames from the selected bookie
usernames = data_bookie['username'].unique()

# Add a dropdown menu for selecting a username
selected_username = st.sidebar.selectbox("Select Username", usernames)

# Filter your data based on the selected username
data_filtered = data_bookie[data_bookie['username'] == selected_username]

# Get placed trades and not placed trades
trades_p = data_filtered[data_filtered["placed"] == "placed"]
trades_np = data_filtered[data_filtered["placed"] != "placed"]
...


# Creating a three column layout
col1, col2, col3 = st.columns(3)

# Plot balance over time for last 20 placed trades in the first column
col1.header("Balance Over Time")
col1.line_chart(trades_p["balance"])

# Table of Last 20 Placed and Not Placed Trades in the second column
pd.set_option("display.max_rows", 10)
col2.header("100 Most Recent Trades Placed")
col2.table(
    trades_p[["win_odds", "bsp", "balance", "best_lay_price", "stake_size"]].tail(10)
)
# col2.header("Not Placed Trades")
# col2.table(trades_np)

# Histogram of EV's (assuming a column "EV" exists) in the third column
col3.header("Histogram of EV's")
trades_evs = trades_p[trades_p["bsp"] != 0.0]
trades_evs = trades_evs[trades_evs["bsp"].notnull()]

for index, row in trades_evs.iterrows():
    trades_evs.loc[index, "ev"] = float(row.win_odds) / float(row.bsp)

missed_evs = trades_np[trades_np["bsp"] != 0.0]
missed_evs = missed_evs[missed_evs["bsp"].notnull()]
# filter out duplicates of market ids
missed_evs = missed_evs.drop_duplicates(subset=["market_id"])

for index, row in missed_evs.iterrows():
    missed_evs.loc[index, "ev"] = float(row.win_odds) / float(row.bsp)


figure = plt.figure(figsize=(10, 5))
## plot distplot but remove outliers


def remove_outliers(df, column_name):
    Q1 = df[column_name].quantile(0.25)
    Q3 = df[column_name].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    filtered_df = df[
        (df[column_name] >= lower_bound) & (df[column_name] <= upper_bound)
    ]
    return filtered_df


# Remove outliers from 'ev' column in each DataFrame
filtered_trades_evs = remove_outliers(trades_evs, "ev")
filtered_missed_evs = remove_outliers(missed_evs, "ev")


# Now you can plot the filtered data
sns.distplot(filtered_trades_evs["ev"], label="Placed")
sns.distplot(filtered_missed_evs["ev"], label="Missed")

col3.pyplot(figure)

# See what EV is when removing bets where second_best_lay_price/best_lay_price > 1.05
filter = trades_evs[
    trades_evs["second_to_best_lay_prices"].astype(float)
    / trades_evs["best_lay_price"].astype(float)
    < 1.05
]
mean_ev = filter["ev"].mean()
column = st.columns(2)
column[0].header("Mean EV")
column[0].write(mean_ev)
column[1].header("num")
column[1].write(len(trades_evs))

## Add EV for all orders placed within past 24 hours from now
now = datetime.datetime.utcnow()
trades_p["timestamp"] = pd.to_datetime(trades_p["timestamp"])
last_24 = trades_p.loc[trades_p["timestamp"] > now - datetime.timedelta(days=1)].copy()

# Display Mean Forecasted EV from Past 24 hours
last_24["EV"] = last_24["win_odds"] / last_24["best_lay_price"]

# Now compute actual EV with bsp
# last_24["actual_ev"] = last_24["win_odds"] / last_24["bsp"]
day_evmean = round(last_24["EV"].mean(), 3)

trades_evs["expected_return"] = 1 / trades_evs["bsp"].astype(float) * (
    trades_evs["win_odds"].astype(float) - 1
) * trades_evs["stake_size"].astype(float) - (
    1 - 1 / trades_evs["bsp"].astype(float)
) * trades_evs[
    "stake_size"
].astype(
    float
)


total_waged = sum(trades_evs["stake_size"].astype(float))
missed_evs["stake_size"] = 20


def calculate_expected_value(p_win, odds_win, p_loss, stake_size):
    ev = (p_win * (odds_win - 1) - p_loss) * stake_size
    return ev


missed_evs["expected_return"] = (
    1 / missed_evs["bsp"].astype(float) * (missed_evs["win_odds"].astype(float) - 1)
    - (1 - 1 / missed_evs["bsp"].astype(float))
) * missed_evs["stake_size"].astype(float)


# Closing Line

trades_evs["clv"] = trades_evs["stake_size"].astype(float) * (
    trades_evs["win_odds"].astype(float) / trades_evs["bsp"].astype(float) - 1
)
# Calculate cumulative total of CLV
trades_evs["cumulative_clv"] = trades_evs["clv"].cumsum()

# st.line_chart(trades_evs["cumulative_clv"])

# Calculate cumulative total of actual return
trades_evs["profit"] = trades_evs["return"].astype(float) - trades_evs[
    "stake_size"
].astype(float)
trades_evs["cumulative_return"] = trades_evs["profit"].cumsum()


# Create a line chart
plt.figure(figsize=(15, 7))
plt.plot(trades_evs.index, trades_evs["cumulative_clv"], label="Cumulative CLV")
plt.plot(
    trades_evs.index,
    trades_evs["cumulative_return"],
    label="Cumulative Return",
    color="orange",
)

# Fill the area under the lines
plt.fill_between(trades_evs.index, trades_evs["cumulative_clv"], alpha=0.3)
plt.fill_between(
    trades_evs.index, trades_evs["cumulative_return"], alpha=0.3, color="orange"
)

plt.title("Cumulative Closing Line Value and Return Over Time")
plt.ylabel("Cumulative Value")
plt.xlabel("Index")
plt.legend()
# Display the chart in the Streamlit app
st.pyplot(plt.gcf())
trades_evs["expected_return_cumulative"] = trades_evs["expected_return"].cumsum()

# Create a line chart
plt.figure(figsize=(15, 7))
plt.plot(
    trades_evs.index,
    trades_evs["expected_return_cumulative"],
    label="Cumulative Expected Return",
    color="green",
)
plt.plot(
    trades_evs.index,
    trades_evs["cumulative_return"],
    label="Cumulative Return",
    color="orange",
)

# Fill the area under the lines
plt.fill_between(
    trades_evs.index, trades_evs["expected_return_cumulative"], alpha=0.3, color="green"
)
plt.fill_between(
    trades_evs.index, trades_evs["cumulative_return"], alpha=0.3, color="orange"
)

plt.title("Cumulative Expected Return and Return Over Time")
plt.ylabel("Cumulative Value")
plt.xlabel("Index")
plt.legend()

# Display the chart in the Streamlit app
st.pyplot(plt.gcf())

ev_bets_placed = round(sum(trades_evs["expected_return"].astype(float)), 3)
ev_missed_bets = round(sum(missed_evs["expected_return"].astype(float)), 3)
ev_all_time_placed = round(trades_evs["ev"].mean(), 3)
ev_all_time_missed = round(filtered_missed_evs["ev"].mean(), 3)

profit_loss_placed = round(
    sum(trades_evs["return"].astype(float))
    - sum(trades_evs["stake_size"].astype(float)),
    4,
)
total_bets_placed = len(trades_p)
# average_odds = round(trades_evs["win_odds"].astype(float).mean(), 3)
average_bsp = round(trades_evs["bsp"].astype(float).mean(), 3)

cols = st.columns(5)

# filter out duplicates of runners

percentage_missed = round(
    len(missed_evs) / (len(missed_evs) + len(trades_evs)) * 100, 2
)
cols[0].metric(
    label="Expected Profit (EV of Bets Placed)", value=ev_bets_placed, delta=None
)
cols[1].metric(
    label="Expected Profit (EV of Missed Bets)", value=ev_missed_bets, delta=None
)
cols[2].metric(
    label="All Time EV of Trades Placed", value=ev_all_time_placed, delta=None
)
cols[3].metric(
    label="All Time EV of Trades Missed", value=ev_all_time_missed, delta=None
)
cols[4].metric(
    label="All time Profit/Loss for Placed Bets", value=profit_loss_placed, delta=None
)
# cols[5].metric(label="Average Odds SB", value=average_odds, delta=None)
cols_new = st.columns(3)
cols_new[0].metric(label="Average Odds BSP", value=average_bsp, delta=None)
cols_new[1].metric(label="Percentage Missed", value=percentage_missed, delta=None)
cols_new[2].metric(label="Total Bets Placed", value=total_bets_placed, delta=None)


## plot
## plot average ev for each bucket of odds
## bucket size is 1 dollar wide,
## so 1-2, 2-3, 3-4, 4-5, 5-6, 6-7, 7-8, 8-9, 9-10, 10+


# Display the full data at the end (not in a column)
# st.write(data)
# Compute pairwise correlation of columns, excluding NA/null values.
# Select only numeric columns
## Find Performance from Last 48 hours
trades_evs["timestamp"] = pd.to_datetime(trades_evs["timestamp"])
last_24 = trades_evs.loc[
    trades_evs["timestamp"] > now - datetime.timedelta(days=2)
].copy()

# Opening Balance
opening_balance = last_24["balance"].iloc[0]

# Closing Balance
closing_balance = last_24["balance"].iloc[-1]

# filter out trades where bsp is 0 or null
last_24 = last_24[last_24["bsp"] > 0]
last_24 = last_24[last_24["bsp"].notnull()]

# Calculate performance from last night
# Bets Placed
num_bets = len(last_24)

# Bets Won
num_wins = len(last_24[last_24["return"] > 0])

# Bets Lost
num_losses = len(last_24[last_24["return"] == 0])

# Total Return
last_24["return"] = sum(last_24["return"].astype(float))

# Average Odds
average_odds = round(last_24["bsp"].astype(float).mean(), 3)

# Display on Dashvoard
st.header("Last 48 Hours (Dependent on Cleaning of Data (around 5pm AEST))")
cols = st.columns(6)
cols[0].metric(label="Opening Balance", value=opening_balance, delta=None)
cols[1].metric(label="Closing Balance", value=closing_balance, delta=None)
cols[2].metric(label="Bets Placed", value=num_bets, delta=None)
cols[3].metric(label="Bets Won", value=num_wins, delta=None)
cols[4].metric(label="Bets Lost", value=num_losses, delta=None)
cols[5].metric(label="Average Odds", value=average_odds, delta=None)

st.header("Last 24 Hours - no data cleaned (only SB information)")

trades_p["timestamp"] = pd.to_datetime(trades_p["timestamp"])
last_24 = trades_p.loc[trades_p["timestamp"] > now - datetime.timedelta(days=1)].copy()

# Opening Balance
opening_balance = last_24["balance"].iloc[0]

# Closing Balance
closing_balance = last_24["balance"].iloc[-1]

# Bets placed
num_bets = len(last_24)

# Average Odds
average_odds = round(last_24["win_odds"].astype(float).mean(), 3)

# Display

cols = st.columns(4)
cols[0].metric(label="Opening Balance", value=opening_balance, delta=None)
cols[1].metric(label="Closing Balance", value=closing_balance, delta=None)
cols[2].metric(label="Bets Placed", value=num_bets, delta=None)
cols[3].metric(label="Average Odds (SB)", value=average_odds, delta=None)
