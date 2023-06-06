from pymongo import MongoClient
import pandas as pd
import datetime
import numpy as np
import matplotlib.pyplot as plt


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
    usernames = usernames.remove("nan")

    bookies = data["bookie"].unique()
    bookies = np.append(bookies, "All")
    bookies = bookies.remove("nan")
    return usernames, bookies

def plot_total_profit_loss(trades):

    trades["clv"] = trades["stake_size"] * (trades["win_odds"]/trades["bsp"] - 1)
    trades["cumulative_clv"] = trades["clv"].cumsum()
    trades["cumulative_profit"] =(trades["return"] - trades["stake_size"]).cumsum()

    # Plot both, one filled with orange, one with blue, along index
    fig, ax = plt.subplots(figsize=(20, 10))
    ax.plot(trades.index, trades["cumulative_clv"], color="orange")
    ax.fill_between(trades.index, trades["cumulative_clv"], color="orange", alpha=0.3)
    # ax.plot(trades.index, trades["cumulative_profit"], color="blue")
    ax.fill_between(trades.index, trades["cumulative_profit"], color="blue", alpha=0.3)
    ax.set_title("Cumulative CLV vs Cumulative Profit")
    ax.set_xlabel("Trade Number")

    return fig, trades

def plot_balance(trades):
    fig, ax = plt.subplots(figsize=(20, 10))
    ax.plot(trades.index, trades["balance"], color="orange")
    ax.set_title("Balance")
    ax.set_xlabel("Trade Number")
    return fig

def calculate_ev(trades):
    trades["ev"] = trades["win_odds"] / trades["bsp"]
    return trades