import yfinance as yf
import pandas as pd
import glob
import os


def get_prior_day_break_signals(stop_points=30, target_points=60, period="60d", interval="15m", entry_time="08:30"):
    nq = yf.Ticker("NQ=F")
    history = nq.history(period=period, interval=interval)
    history["date"] = history.index.date

    daily_levels = history.groupby("date").agg(
        day_high=("High", "max"),
        day_low=("Low", "min")
    )
    daily_levels["prior_day_high"] = daily_levels["day_high"].shift(1)
    daily_levels["prior_day_low"] = daily_levels["day_low"].shift(1)

    opens_830 = history[history.index.time == pd.Timestamp(entry_time).time()].copy()
    opens_830 = opens_830.join(daily_levels[["prior_day_high", "prior_day_low"]], on="date")

    def get_signal(row):
        if row["Close"] > row["prior_day_high"]:
            return "LONG"
        elif row["Close"] < row["prior_day_low"]:
            return "SHORT"
        else:
            return "NONE"

    opens_830["signal"] = opens_830.apply(get_signal, axis=1)
    signals_only = opens_830[opens_830["signal"] != "NONE"].copy()

    def simulate_trade(row):
        entry_price = row["Close"]
        signal = row["signal"]
        day = row["date"]

        if signal == "LONG":
            stop_price = entry_price - stop_points
            target_price = entry_price + target_points
        else:
            stop_price = entry_price + stop_points
            target_price = entry_price - target_points

        day_bars = history[
            (history["date"] == day)
            & (history.index.time > pd.Timestamp(entry_time).time())
            & (history.index.time <= pd.Timestamp("16:00").time())
        ]

        for _, bar in day_bars.iterrows():
            if signal == "LONG":
                hit_stop = bar["Low"] <= stop_price
                hit_target = bar["High"] >= target_price
            else:
                hit_stop = bar["High"] >= stop_price
                hit_target = bar["Low"] <= target_price

            if hit_stop:
                return pd.Series({"exit_price": stop_price, "exit_reason": "stop"})
            elif hit_target:
                return pd.Series({"exit_price": target_price, "exit_reason": "target"})

        final_close = day_bars.iloc[-1]["Close"]
        return pd.Series({"exit_price": final_close, "exit_reason": "eod"})

    if len(signals_only) == 0:
        signals_only["exit_price"] = pd.Series(dtype="float64")
        signals_only["exit_reason"] = pd.Series(dtype="object")
    else:
        exit_info = signals_only.apply(simulate_trade, axis=1)
        signals_only["exit_price"] = exit_info["exit_price"]
        signals_only["exit_reason"] = exit_info["exit_reason"]

    return signals_only[["date", "signal", "Close", "exit_price", "exit_reason"]]


def get_prior_day_break_signals_from_archive(stop_points=30, target_points=60, entry_time="08:30", data_folder="data/raw"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))

    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}. Run save_daily_date.py first.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history["date"] = history.index.date

    daily_levels = history.groupby("date").agg(
        day_high=("High", "max"),
        day_low=("Low", "min")
    )
    daily_levels["prior_day_high"] = daily_levels["day_high"].shift(1)
    daily_levels["prior_day_low"] = daily_levels["day_low"].shift(1)

    opens_830 = history[history.index.time == pd.Timestamp(entry_time).time()].copy()
    opens_830 = opens_830.join(daily_levels[["prior_day_high", "prior_day_low"]], on="date")

    def get_signal(row):
        if row["Close"] > row["prior_day_high"]:
            return "LONG"
        elif row["Close"] < row["prior_day_low"]:
            return "SHORT"
        else:
            return "NONE"

    opens_830["signal"] = opens_830.apply(get_signal, axis=1)
    signals_only = opens_830[opens_830["signal"] != "NONE"].copy()

    def simulate_trade(row):
        entry_price = row["Close"]
        signal = row["signal"]
        day = row["date"]

        if signal == "LONG":
            stop_price = entry_price - stop_points
            target_price = entry_price + target_points
        else:
            stop_price = entry_price + stop_points
            target_price = entry_price - target_points

        day_bars = history[
            (history["date"] == day)
            & (history.index.time > pd.Timestamp(entry_time).time())
            & (history.index.time <= pd.Timestamp("16:00").time())
        ]

        for _, bar in day_bars.iterrows():
            if signal == "LONG":
                hit_stop = bar["Low"] <= stop_price
                hit_target = bar["High"] >= target_price
            else:
                hit_stop = bar["High"] >= stop_price
                hit_target = bar["Low"] <= target_price

            if hit_stop:
                return pd.Series({"exit_price": stop_price, "exit_reason": "stop"})
            elif hit_target:
                return pd.Series({"exit_price": target_price, "exit_reason": "target"})

        final_close = day_bars.iloc[-1]["Close"]
        return pd.Series({"exit_price": final_close, "exit_reason": "eod"})

    if len(signals_only) == 0:
        signals_only["exit_price"] = pd.Series(dtype="float64")
        signals_only["exit_reason"] = pd.Series(dtype="object")
    else:
        exit_info = signals_only.apply(simulate_trade, axis=1)
        signals_only["exit_price"] = exit_info["exit_price"]
        signals_only["exit_reason"] = exit_info["exit_reason"]

    return signals_only[["date", "signal", "Close", "exit_price", "exit_reason"]]


def get_overnight_range_signals_from_archive(stop_points=30, target_points=60, entry_time="08:30", data_folder="data/raw"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))

    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}. Run save_daily_date.py first.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history["date"] = history.index.date

    def get_session_date(ts):
        if ts.time() >= pd.Timestamp("18:00").time():
            return (ts + pd.Timedelta(days=1)).date()
        else:
            return ts.date()

    history["session_date"] = [get_session_date(ts) for ts in history.index]

    overnight_bars = history[
        (history.index.time >= pd.Timestamp("18:00").time())
        | (history.index.time < pd.Timestamp(entry_time).time())
    ]

    overnight_levels = overnight_bars.groupby("session_date").agg(
        overnight_high=("High", "max"),
        overnight_low=("Low", "min")
    )

    opens_830 = history[history.index.time == pd.Timestamp(entry_time).time()].copy()
    opens_830 = opens_830.join(overnight_levels, on="date")

    def get_signal(row):
        if row["Close"] > row["overnight_high"]:
            return "LONG"
        elif row["Close"] < row["overnight_low"]:
            return "SHORT"
        else:
            return "NONE"

    opens_830["signal"] = opens_830.apply(get_signal, axis=1)
    signals_only = opens_830[opens_830["signal"] != "NONE"].copy()

    def simulate_trade(row):
        entry_price = row["Close"]
        signal = row["signal"]
        day = row["date"]

        if signal == "LONG":
            stop_price = entry_price - stop_points
            target_price = entry_price + target_points
        else:
            stop_price = entry_price + stop_points
            target_price = entry_price - target_points

        day_bars = history[
            (history["date"] == day)
            & (history.index.time > pd.Timestamp(entry_time).time())
            & (history.index.time <= pd.Timestamp("16:00").time())
        ]

        for _, bar in day_bars.iterrows():
            if signal == "LONG":
                hit_stop = bar["Low"] <= stop_price
                hit_target = bar["High"] >= target_price
            else:
                hit_stop = bar["High"] >= stop_price
                hit_target = bar["Low"] <= target_price

            if hit_stop:
                return pd.Series({"exit_price": stop_price, "exit_reason": "stop"})
            elif hit_target:
                return pd.Series({"exit_price": target_price, "exit_reason": "target"})

        final_close = day_bars.iloc[-1]["Close"]
        return pd.Series({"exit_price": final_close, "exit_reason": "eod"})

    if len(signals_only) == 0:
        signals_only["exit_price"] = pd.Series(dtype="float64")
        signals_only["exit_reason"] = pd.Series(dtype="object")
    else:
        exit_info = signals_only.apply(simulate_trade, axis=1)
        signals_only["exit_price"] = exit_info["exit_price"]
        signals_only["exit_reason"] = exit_info["exit_reason"]

    return signals_only[["date", "signal", "Close", "exit_price", "exit_reason"]]


def get_prior_day_break_signals_atr_from_archive(atr_multiplier=1.5, target_multiplier=3.0, atr_period=14, entry_time="08:30", data_folder="data/raw"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))

    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}. Run save_daily_date.py first.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history["date"] = history.index.date

    daily = history.groupby("date").agg(
        day_high=("High", "max"),
        day_low=("Low", "min")
    )
    daily["prior_day_high"] = daily["day_high"].shift(1)
    daily["prior_day_low"] = daily["day_low"].shift(1)

    session_bars = history[
        (history.index.time >= pd.Timestamp(entry_time).time())
        & (history.index.time <= pd.Timestamp("16:00").time())
    ]
    session_stats = session_bars.groupby("date").agg(
        session_high=("High", "max"),
        session_low=("Low", "min"),
        session_close=("Close", "last")
    )
    session_stats["prev_session_close"] = session_stats["session_close"].shift(1)

    def session_true_range(row):
        if pd.isna(row["prev_session_close"]):
            return row["session_high"] - row["session_low"]
        return max(
            row["session_high"] - row["session_low"],
            abs(row["session_high"] - row["prev_session_close"]),
            abs(row["session_low"] - row["prev_session_close"])
        )

    session_stats["true_range"] = session_stats.apply(session_true_range, axis=1)
    session_stats["atr"] = session_stats["true_range"].rolling(atr_period).mean().shift(1)

    daily = daily.join(session_stats[["atr"]])

    opens_830 = history[history.index.time == pd.Timestamp(entry_time).time()].copy()
    opens_830 = opens_830.join(daily[["prior_day_high", "prior_day_low", "atr"]], on="date")

    def get_signal(row):
        if pd.isna(row["atr"]):
            return "NONE"
        if row["Close"] > row["prior_day_high"]:
            return "LONG"
        elif row["Close"] < row["prior_day_low"]:
            return "SHORT"
        else:
            return "NONE"

    opens_830["signal"] = opens_830.apply(get_signal, axis=1)
    signals_only = opens_830[opens_830["signal"] != "NONE"].copy()

    def simulate_trade(row):
        entry_price = row["Close"]
        signal = row["signal"]
        day = row["date"]
        stop_points = row["atr"] * atr_multiplier
        target_points = row["atr"] * target_multiplier

        if signal == "LONG":
            stop_price = entry_price - stop_points
            target_price = entry_price + target_points
        else:
            stop_price = entry_price + stop_points
            target_price = entry_price - target_points

        day_bars = history[
            (history["date"] == day)
            & (history.index.time > pd.Timestamp(entry_time).time())
            & (history.index.time <= pd.Timestamp("16:00").time())
        ]

        for _, bar in day_bars.iterrows():
            if signal == "LONG":
                hit_stop = bar["Low"] <= stop_price
                hit_target = bar["High"] >= target_price
            else:
                hit_stop = bar["High"] >= stop_price
                hit_target = bar["Low"] <= target_price

            if hit_stop:
                return pd.Series({"exit_price": stop_price, "exit_reason": "stop"})
            elif hit_target:
                return pd.Series({"exit_price": target_price, "exit_reason": "target"})

        final_close = day_bars.iloc[-1]["Close"]
        return pd.Series({"exit_price": final_close, "exit_reason": "eod"})

    if len(signals_only) == 0:
        signals_only["exit_price"] = pd.Series(dtype="float64")
        signals_only["exit_reason"] = pd.Series(dtype="object")
    else:
        exit_info = signals_only.apply(simulate_trade, axis=1)
        signals_only["exit_price"] = exit_info["exit_price"]
        signals_only["exit_reason"] = exit_info["exit_reason"]

    return signals_only[["date", "signal", "Close", "exit_price", "exit_reason", "atr"]]


def get_orb_signals_from_archive(stop_points=30, target_points=60, or_minutes=30, session_start="08:30", data_folder="data/raw"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))

    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}. Run save_daily_date.py first.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history["date"] = history.index.date

    session_start_time = pd.Timestamp(session_start).time()
    or_end_time = (pd.Timestamp(session_start) + pd.Timedelta(minutes=or_minutes)).time()
    session_end_time = pd.Timestamp("16:00").time()

    opening_range_bars = history[
        (history.index.time >= session_start_time)
        & (history.index.time < or_end_time)
    ]
    or_levels = opening_range_bars.groupby("date").agg(
        or_high=("High", "max"),
        or_low=("Low", "min")
    )

    results = []

    for day, group in history.groupby("date"):
        if day not in or_levels.index:
            continue

        or_high = or_levels.loc[day, "or_high"]
        or_low = or_levels.loc[day, "or_low"]

        after_bars = group[
            (group.index.time >= or_end_time)
            & (group.index.time <= session_end_time)
        ]

        signal = None
        entry_price = None
        entry_timestamp = None

        for idx, bar in after_bars.iterrows():
            if bar["Close"] > or_high:
                signal = "LONG"
                entry_price = bar["Close"]
                entry_timestamp = idx
                break
            elif bar["Close"] < or_low:
                signal = "SHORT"
                entry_price = bar["Close"]
                entry_timestamp = idx
                break

        if signal is None:
            continue

        if signal == "LONG":
            stop_price = entry_price - stop_points
            target_price = entry_price + target_points
        else:
            stop_price = entry_price + stop_points
            target_price = entry_price - target_points

        remaining_bars = group[
            (group.index > entry_timestamp)
            & (group.index.time <= session_end_time)
        ]

        exit_price = None
        exit_reason = None

        for _, bar in remaining_bars.iterrows():
            if signal == "LONG":
                hit_stop = bar["Low"] <= stop_price
                hit_target = bar["High"] >= target_price
            else:
                hit_stop = bar["High"] >= stop_price
                hit_target = bar["Low"] <= target_price

            if hit_stop:
                exit_price = stop_price
                exit_reason = "stop"
                break
            elif hit_target:
                exit_price = target_price
                exit_reason = "target"
                break

        if exit_price is None:
            if len(remaining_bars) > 0:
                exit_price = remaining_bars.iloc[-1]["Close"]
            else:
                exit_price = entry_price
            exit_reason = "eod"

        results.append({
            "date": day,
            "signal": signal,
            "Close": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason
        })

    return pd.DataFrame(results, columns=["date", "signal", "Close", "exit_price", "exit_reason"])


def get_prior_day_fade_signals_from_archive(stop_points=30, target_points=60, entry_time="08:30", data_folder="data/raw"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))

    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}. Run save_daily_date.py first.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history["date"] = history.index.date

    daily_levels = history.groupby("date").agg(
        day_high=("High", "max"),
        day_low=("Low", "min")
    )
    daily_levels["prior_day_high"] = daily_levels["day_high"].shift(1)
    daily_levels["prior_day_low"] = daily_levels["day_low"].shift(1)

    opens_830 = history[history.index.time == pd.Timestamp(entry_time).time()].copy()
    opens_830 = opens_830.join(daily_levels[["prior_day_high", "prior_day_low"]], on="date")

    def get_signal(row):
        # FADE logic: break above prior high -> SHORT (bet on reversal)
        # break below prior low -> LONG (bet on reversal)
        if row["Close"] > row["prior_day_high"]:
            return "SHORT"
        elif row["Close"] < row["prior_day_low"]:
            return "LONG"
        else:
            return "NONE"

    opens_830["signal"] = opens_830.apply(get_signal, axis=1)
    signals_only = opens_830[opens_830["signal"] != "NONE"].copy()

    def simulate_trade(row):
        entry_price = row["Close"]
        signal = row["signal"]
        day = row["date"]

        if signal == "LONG":
            stop_price = entry_price - stop_points
            target_price = entry_price + target_points
        else:
            stop_price = entry_price + stop_points
            target_price = entry_price - target_points

        day_bars = history[
            (history["date"] == day)
            & (history.index.time > pd.Timestamp(entry_time).time())
            & (history.index.time <= pd.Timestamp("16:00").time())
        ]

        for _, bar in day_bars.iterrows():
            if signal == "LONG":
                hit_stop = bar["Low"] <= stop_price
                hit_target = bar["High"] >= target_price
            else:
                hit_stop = bar["High"] >= stop_price
                hit_target = bar["Low"] <= target_price

            if hit_stop:
                return pd.Series({"exit_price": stop_price, "exit_reason": "stop"})
            elif hit_target:
                return pd.Series({"exit_price": target_price, "exit_reason": "target"})

        final_close = day_bars.iloc[-1]["Close"]
        return pd.Series({"exit_price": final_close, "exit_reason": "eod"})

    if len(signals_only) == 0:
        signals_only["exit_price"] = pd.Series(dtype="float64")
        signals_only["exit_reason"] = pd.Series(dtype="object")
    else:
        exit_info = signals_only.apply(simulate_trade, axis=1)
        signals_only["exit_price"] = exit_info["exit_price"]
        signals_only["exit_reason"] = exit_info["exit_reason"]

    return signals_only[["date", "signal", "Close", "exit_price", "exit_reason"]]