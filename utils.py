from pymongo import MongoClient
import pandas as pd
import datetime
import numpy as np
import matplotlib.pyplot as plt

def connect_to_mongodb(mongo_url):
    client = MongoClient(mongo_url)
    db = client.BettingData
    collection = db.Trades
    return collection

def fetch_data(collection):
    data = collection.find()
    data = pd.DataFrame(list(data))
    return data

def filter_data_by_bookie(data, bookie):
    if bookie != "All":
        data = data[data['bookie'] == bookie]
    return data

def filter_data_by_username(data, username):
    if username != "All":
        data = data[data['username'] == username]
    return data

def calculate_expected_value(p_win, odds_win, p_loss, stake_size):
    ev = (p_win * (odds_win - 1) - p_loss) * stake_size
    return ev

def prepare_data(data):
    trades_p = data[data["placed"] == "placed"]
    trades_np = data[data["placed"] != "placed"]
    return trades_p, trades_np

def fetch_data(data, bookie, username):
    data = filter_data_by_bookie(data, bookie)
    data = filter_data_by_username(data, username)
    trades_p, trades_np = prepare_data(data)
    return trades_p, trades_np

def get_usernames_and_bookies(data):
    usernames = data["username"].unique()
    usernames = np.append(usernames, "All")
    bookies = data["bookie"].unique()
    bookies = np.append(bookies, "All")
    return usernames, bookies

def calculate_ev(trades_p):
    trades_p["ev"] = trades_p.apply(
        lambda row: calculate_expected_value(
            row["p_win"], row["win_odds"], row["p_loss"], row["stake_size"]
        ),
        axis=1,
    )
    return trades_p

def calculate_total_profit(trades_p):
    total_profit = trades_p["return"].sum() - trades_p["stake_size"].sum()
    return total_profit

def cumulative_profit_figure(trades):
    trades["clv"] = trades["stake_size"].astype(float) * (
        trades["win_odds"].astype(float) / trades["bsp"].astype(float) - 1
    )
    trades["cumulative_clv"] = trades["clv"].cumsum()
    # Calculate cumulative total of actual return
    trades["profit"] = trades["return"].astype(float) - trades[
        "stake_size"
    ].astype(float)
    trades["cumulative_return"] = trades["profit"].cumsum()
    
    figure = plt.figure(figsize=(15, 7))
    plt.plot(trades.index, trades["cumulative_clv"], label="Cumulative CLV")
    plt.plot(
        trades.index,
        trades["cumulative_return"],
        label="Cumulative Return",
        color="orange",
    )
    # Fill the area under the lines
    plt.fill_between(trades.index, trades["cumulative_clv"], alpha=0.3)
    plt.fill_between(
        trades.index, trades["cumulative_return"], alpha=0.3, color="orange"
    )

    plt.title("Cumulative Closing Line Value and Return Over Time")
    plt.ylabel("Cumulative Value")
    plt.xlabel("Index")
    plt.legend()
    return figure, trades