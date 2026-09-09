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
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
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
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
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
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
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
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
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
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
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

def get_prior_day_fade_signals_atr_from_archive(atr_multiplier=0.15, target_multiplier=0.30, atr_period=14, entry_time="08:30", data_folder="data/raw"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))

    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}. Run save_daily_date.py first.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
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
        # FADE logic: break above prior high -> SHORT, break below prior low -> LONG
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


def get_trend_following_signals_from_archive(ma_period=10, stop_points=200, data_folder="data/raw"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))

    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}. Run save_daily_date.py first.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
    history["date"] = history.index.date

    daily = history.groupby("date").agg(
        open=("Open", "first"),
        high=("High", "max"),
        low=("Low", "min"),
        close=("Close", "last")
    )
    daily = daily.sort_index()

    daily["ma"] = daily["close"].rolling(ma_period).mean()
    daily["prior_close"] = daily["close"].shift(1)
    daily["prior_ma"] = daily["ma"].shift(1)

    trading_days = daily.index.tolist()
    results = []

    i = 0
    while i < len(trading_days) - 1:
        day = trading_days[i]
        row = daily.loc[day]

        if pd.isna(row["prior_ma"]):
            i += 1
            continue

        if row["prior_close"] > row["prior_ma"]:
            signal = "LONG"
        elif row["prior_close"] < row["prior_ma"]:
            signal = "SHORT"
        else:
            i += 1
            continue

        entry_day_idx = i
        entry_day = trading_days[entry_day_idx]
        entry_price = daily.loc[entry_day, "open"]

        if signal == "LONG":
            stop_price = entry_price - stop_points
        else:
            stop_price = entry_price + stop_points

        exit_price = None
        exit_reason = None
        exit_day = None
        j = entry_day_idx

        while j < len(trading_days):
            check_day = trading_days[j]
            check_row = daily.loc[check_day]

            if signal == "LONG" and check_row["low"] <= stop_price:
                exit_price = stop_price
                exit_reason = "stop"
                exit_day = check_day
                break
            elif signal == "SHORT" and check_row["high"] >= stop_price:
                exit_price = stop_price
                exit_reason = "stop"
                exit_day = check_day
                break

            if not pd.isna(check_row["ma"]):
                if signal == "LONG" and check_row["close"] < check_row["ma"]:
                    exit_price = check_row["close"]
                    exit_reason = "trend_reversal"
                    exit_day = check_day
                    break
                elif signal == "SHORT" and check_row["close"] > check_row["ma"]:
                    exit_price = check_row["close"]
                    exit_reason = "trend_reversal"
                    exit_day = check_day
                    break

            j += 1

        if exit_price is None:
            exit_price = daily.loc[trading_days[-1], "close"]
            exit_reason = "end_of_data"
            exit_day = trading_days[-1]
            j = len(trading_days) - 1

        results.append({
            "entry_date": entry_day,
            "exit_date": exit_day,
            "signal": signal,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "days_held": j - entry_day_idx
        })

        i = j + 1

    return pd.DataFrame(results)


def get_trend_following_atr_signals_from_archive(ma_period=5, atr_multiplier=1.0, atr_period=14, data_folder="data/raw"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
    history["date"] = history.index.date

    daily = history.groupby("date").agg(open=("Open", "first"), high=("High", "max"), low=("Low", "min"), close=("Close", "last"))
    daily = daily.sort_index()
    daily["ma"] = daily["close"].rolling(ma_period).mean()
    daily["prior_close"] = daily["close"].shift(1)
    daily["prior_ma"] = daily["ma"].shift(1)
    daily["prev_close_tr"] = daily["close"].shift(1)

    def true_range(row):
        if pd.isna(row["prev_close_tr"]):
            return row["high"] - row["low"]
        return max(row["high"] - row["low"], abs(row["high"] - row["prev_close_tr"]), abs(row["low"] - row["prev_close_tr"]))

    daily["tr"] = daily.apply(true_range, axis=1)
    daily["atr"] = daily["tr"].rolling(atr_period).mean().shift(1)

    trading_days = daily.index.tolist()
    results = []
    i = 0
    while i < len(trading_days) - 1:
        day = trading_days[i]
        row = daily.loc[day]
        if pd.isna(row["prior_ma"]) or pd.isna(row["atr"]):
            i += 1
            continue
        if row["prior_close"] > row["prior_ma"]:
            signal = "LONG"
        elif row["prior_close"] < row["prior_ma"]:
            signal = "SHORT"
        else:
            i += 1
            continue

        entry_day_idx = i
        entry_day = trading_days[entry_day_idx]
        entry_price = daily.loc[entry_day, "open"]
        stop_points = daily.loc[entry_day, "atr"] * atr_multiplier
        stop_price = entry_price - stop_points if signal == "LONG" else entry_price + stop_points

        exit_price = None
        exit_reason = None
        exit_day = None
        j = entry_day_idx
        while j < len(trading_days):
            check_day = trading_days[j]
            check_row = daily.loc[check_day]
            if signal == "LONG" and check_row["low"] <= stop_price:
                exit_price, exit_reason, exit_day = stop_price, "stop", check_day
                break
            elif signal == "SHORT" and check_row["high"] >= stop_price:
                exit_price, exit_reason, exit_day = stop_price, "stop", check_day
                break
            if not pd.isna(check_row["ma"]):
                if signal == "LONG" and check_row["close"] < check_row["ma"]:
                    exit_price, exit_reason, exit_day = check_row["close"], "trend_reversal", check_day
                    break
                elif signal == "SHORT" and check_row["close"] > check_row["ma"]:
                    exit_price, exit_reason, exit_day = check_row["close"], "trend_reversal", check_day
                    break
            j += 1
        if exit_price is None:
            exit_price = daily.loc[trading_days[-1], "close"]
            exit_reason = "end_of_data"
            exit_day = trading_days[-1]
            j = len(trading_days) - 1

        results.append({
            "entry_date": entry_day, "exit_date": exit_day, "signal": signal,
            "entry_price": entry_price, "exit_price": exit_price, "exit_reason": exit_reason,
            "days_held": j - entry_day_idx
        })
        i = j + 1
    return pd.DataFrame(results)


def get_vwap_reversion_signals_from_archive(stretch_points=50, stop_points=30, target_points=40, entry_time="08:30", session_end="16:00", data_folder="data/raw"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))

    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}. Run save_daily_date.py first.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
    history["date"] = history.index.date

    session_bars = history[
        (history.index.time >= pd.Timestamp(entry_time).time())
        & (history.index.time <= pd.Timestamp(session_end).time())
    ].copy()

    def compute_daily_vwap(group):
        typical_price = (group["High"] + group["Low"] + group["Close"]) / 3
        cumulative_pv = (typical_price * group["Volume"]).cumsum()
        cumulative_vol = group["Volume"].cumsum()
        return cumulative_pv / cumulative_vol

    session_bars["vwap"] = session_bars.groupby("date", group_keys=False).apply(
        lambda g: compute_daily_vwap(g)
    )

    results = []

    for day, group in session_bars.groupby("date"):
        in_position = False
        signal = None
        entry_price = None
        stop_price = None
        target_price = None
        entry_time_actual = None

        for idx, bar in group.iterrows():
            if pd.isna(bar["vwap"]):
                continue

            if not in_position:
                distance = bar["Close"] - bar["vwap"]

                if distance > stretch_points:
                    signal = "SHORT"
                elif distance < -stretch_points:
                    signal = "LONG"
                else:
                    continue

                entry_price = bar["Close"]
                entry_time_actual = idx
                if signal == "LONG":
                    stop_price = entry_price - stop_points
                    target_price = entry_price + target_points
                else:
                    stop_price = entry_price + stop_points
                    target_price = entry_price - target_points
                in_position = True
                continue

            if in_position:
                if signal == "LONG":
                    hit_stop = bar["Low"] <= stop_price
                    hit_target = bar["High"] >= target_price
                else:
                    hit_stop = bar["High"] >= stop_price
                    hit_target = bar["Low"] <= target_price

                if hit_stop:
                    results.append({
                        "date": day, "signal": signal, "entry_price": entry_price,
                        "exit_price": stop_price, "exit_reason": "stop"
                    })
                    in_position = False
                elif hit_target:
                    results.append({
                        "date": day, "signal": signal, "entry_price": entry_price,
                        "exit_price": target_price, "exit_reason": "target"
                    })
                    in_position = False

        if in_position:
            final_close = group.iloc[-1]["Close"]
            results.append({
                "date": day, "signal": signal, "entry_price": entry_price,
                "exit_price": final_close, "exit_reason": "eod"
            })

    return pd.DataFrame(results)


def get_regime_filtered_trend_signals_from_archive(ma_period=5, regime_ma_period=20, regime_lookback=10, stop_points=200, data_folder="data/raw"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
    history["date"] = history.index.date

    daily = history.groupby("date").agg(open=("Open", "first"), high=("High", "max"), low=("Low", "min"), close=("Close", "last"))
    daily = daily.sort_index()

    daily["ma"] = daily["close"].rolling(ma_period).mean()
    daily["regime_ma"] = daily["close"].rolling(regime_ma_period).mean()
    daily["regime_ma_lagged"] = daily["regime_ma"].shift(regime_lookback)
    daily["regime_slope"] = daily["regime_ma"] - daily["regime_ma_lagged"]

    daily["prior_close"] = daily["close"].shift(1)
    daily["prior_ma"] = daily["ma"].shift(1)
    daily["prior_regime_slope"] = daily["regime_slope"].shift(1)

    trading_days = daily.index.tolist()
    results = []
    i = 0
    while i < len(trading_days) - 1:
        day = trading_days[i]
        row = daily.loc[day]

        if pd.isna(row["prior_ma"]) or pd.isna(row["prior_regime_slope"]):
            i += 1
            continue

        if row["prior_close"] > row["prior_ma"]:
            signal = "LONG"
        elif row["prior_close"] < row["prior_ma"]:
            signal = "SHORT"
        else:
            i += 1
            continue

        # REGIME FILTER: only take the trade if the longer-term trend agrees
        regime_agrees = (signal == "LONG" and row["prior_regime_slope"] > 0) or \
                         (signal == "SHORT" and row["prior_regime_slope"] < 0)
        if not regime_agrees:
            i += 1
            continue

        entry_day_idx = i
        entry_day = trading_days[entry_day_idx]
        entry_price = daily.loc[entry_day, "open"]
        stop_price = entry_price - stop_points if signal == "LONG" else entry_price + stop_points

        exit_price = None
        exit_reason = None
        exit_day = None
        j = entry_day_idx
        while j < len(trading_days):
            check_day = trading_days[j]
            check_row = daily.loc[check_day]
            if signal == "LONG" and check_row["low"] <= stop_price:
                exit_price, exit_reason, exit_day = stop_price, "stop", check_day
                break
            elif signal == "SHORT" and check_row["high"] >= stop_price:
                exit_price, exit_reason, exit_day = stop_price, "stop", check_day
                break
            if not pd.isna(check_row["ma"]):
                if signal == "LONG" and check_row["close"] < check_row["ma"]:
                    exit_price, exit_reason, exit_day = check_row["close"], "trend_reversal", check_day
                    break
                elif signal == "SHORT" and check_row["close"] > check_row["ma"]:
                    exit_price, exit_reason, exit_day = check_row["close"], "trend_reversal", check_day
                    break
            j += 1
        if exit_price is None:
            exit_price = daily.loc[trading_days[-1], "close"]
            exit_reason = "end_of_data"
            exit_day = trading_days[-1]
            j = len(trading_days) - 1

        results.append({
            "entry_date": entry_day, "exit_date": exit_day, "signal": signal,
            "entry_price": entry_price, "exit_price": exit_price, "exit_reason": exit_reason,
            "days_held": j - entry_day_idx
        })
        i = j + 1
    return pd.DataFrame(results)


def get_pairs_trading_signals_from_archive(nq_folder="data/raw_nq_extended", es_folder="data/raw_es_extended",
                                            lookback=20, entry_z=2.0, exit_z=0.5, stop_z=3.5, max_hold_days=15):
    nq_files = glob.glob(os.path.join(nq_folder, "*.csv"))
    es_files = glob.glob(os.path.join(es_folder, "*.csv"))
    if not nq_files or not es_files:
        raise FileNotFoundError("Missing NQ or ES archive data.")

    def load_daily_closes(files):
        all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
        hist = pd.concat(all_days)
        hist = hist[~hist.index.duplicated(keep="first")]
        hist = hist.sort_index()
        hist.index = pd.to_datetime(hist.index, utc=True).tz_convert("America/New_York")
        hist["date"] = hist.index.date
        daily = hist.groupby("date").agg(close=("Close", "last"))
        return daily

    nq_daily = load_daily_closes(nq_files)
    es_daily = load_daily_closes(es_files)

    merged = nq_daily.join(es_daily, lsuffix="_nq", rsuffix="_es", how="inner")
    merged = merged.sort_index()
    merged["ratio"] = merged["close_nq"] / merged["close_es"]
    merged["ratio_mean"] = merged["ratio"].rolling(lookback).mean()
    merged["ratio_std"] = merged["ratio"].rolling(lookback).std()
    merged["zscore"] = (merged["ratio"] - merged["ratio_mean"]) / merged["ratio_std"]
    merged["prior_zscore"] = merged["zscore"].shift(1)

    NQ_POINT_VALUE = 20
    ES_POINT_VALUE = 50

    trading_days = merged.index.tolist()
    results = []
    i = 0
    while i < len(trading_days) - 1:
        day = trading_days[i]
        row = merged.loc[day]

        if pd.isna(row["prior_zscore"]):
            i += 1
            continue

        if row["prior_zscore"] > entry_z:
            direction_nq, direction_es = "SHORT", "LONG"
        elif row["prior_zscore"] < -entry_z:
            direction_nq, direction_es = "LONG", "SHORT"
        else:
            i += 1
            continue

        entry_day_idx = i
        entry_day = trading_days[entry_day_idx]
        entry_nq_price = merged.loc[entry_day, "close_nq"]
        entry_es_price = merged.loc[entry_day, "close_es"]
        hedge_ratio = (entry_nq_price * NQ_POINT_VALUE) / (entry_es_price * ES_POINT_VALUE)

        exit_day = None
        exit_reason = None
        j = entry_day_idx

        while j < len(trading_days) and j < entry_day_idx + max_hold_days:
            check_day = trading_days[j]
            check_z = merged.loc[check_day, "zscore"]

            if pd.isna(check_z):
                j += 1
                continue

            if direction_nq == "SHORT" and check_z <= exit_z:
                exit_day, exit_reason = check_day, "reverted"
                break
            elif direction_nq == "LONG" and check_z >= -exit_z:
                exit_day, exit_reason = check_day, "reverted"
                break
            elif direction_nq == "SHORT" and check_z >= stop_z:
                exit_day, exit_reason = check_day, "stop"
                break
            elif direction_nq == "LONG" and check_z <= -stop_z:
                exit_day, exit_reason = check_day, "stop"
                break
            j += 1

        if exit_day is None:
            exit_day = trading_days[min(j, len(trading_days) - 1)]
            exit_reason = "max_hold"

        exit_nq_price = merged.loc[exit_day, "close_nq"]
        exit_es_price = merged.loc[exit_day, "close_es"]

        nq_pnl = (exit_nq_price - entry_nq_price) * NQ_POINT_VALUE * (1 if direction_nq == "LONG" else -1)
        es_pnl = (exit_es_price - entry_es_price) * ES_POINT_VALUE * hedge_ratio * (1 if direction_es == "LONG" else -1)
        total_pnl = nq_pnl + es_pnl

        results.append({
            "entry_date": entry_day, "exit_date": exit_day,
            "direction_nq": direction_nq, "direction_es": direction_es,
            "entry_zscore": row["prior_zscore"], "exit_reason": exit_reason,
            "days_held": j - entry_day_idx, "pnl_dollars": total_pnl
        })
        i = j + 1

    return pd.DataFrame(results)


def get_gap_signals_from_archive(min_gap_points=30, stop_points=40, target_points=80,
                                   fill_mode=True, data_folder="data/raw_nq_extended"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
    history["date"] = history.index.date

    daily = history.groupby("date").agg(
        open=("Open", "first"), high=("High", "max"),
        low=("Low", "min"), close=("Close", "last")
    )
    daily = daily.sort_index()
    daily["prior_close"] = daily["close"].shift(1)
    daily["gap_points"] = daily["open"] - daily["prior_close"]

    session_bars = history[
        (history.index.time >= pd.Timestamp("08:30").time())
        & (history.index.time <= pd.Timestamp("16:00").time())
    ]

    results = []
    trading_days = daily.index.tolist()

    for i, day in enumerate(trading_days):
        row = daily.loc[day]
        if pd.isna(row["gap_points"]):
            continue
        if abs(row["gap_points"]) < min_gap_points:
            continue

        gap_up = row["gap_points"] > 0

        if fill_mode:
            # Betting the gap fills: gap up -> SHORT (expect pullback to prior close), gap down -> LONG
            signal = "SHORT" if gap_up else "LONG"
        else:
            # Betting continuation: gap up -> LONG, gap down -> SHORT
            signal = "LONG" if gap_up else "SHORT"

        entry_price = row["open"]

        if signal == "LONG":
            stop_price = entry_price - stop_points
            target_price = entry_price + target_points
        else:
            stop_price = entry_price + stop_points
            target_price = entry_price - target_points

        day_bars = session_bars[session_bars["date"] == day] if "date" in session_bars.columns else \
                   history[(history["date"] == day) & (history.index.time >= pd.Timestamp("08:30").time()) & (history.index.time <= pd.Timestamp("16:00").time())]

        exit_price = None
        exit_reason = None
        for _, bar in day_bars.iterrows():
            if signal == "LONG":
                hit_stop = bar["Low"] <= stop_price
                hit_target = bar["High"] >= target_price
            else:
                hit_stop = bar["High"] >= stop_price
                hit_target = bar["Low"] <= target_price
            if hit_stop:
                exit_price, exit_reason = stop_price, "stop"
                break
            elif hit_target:
                exit_price, exit_reason = target_price, "target"
                break

        if exit_price is None:
            if len(day_bars) > 0:
                exit_price = day_bars.iloc[-1]["Close"]
            else:
                exit_price = row["close"]
            exit_reason = "eod"

        results.append({
            "date": day, "signal": signal, "gap_points": row["gap_points"],
            "entry_price": entry_price, "exit_price": exit_price, "exit_reason": exit_reason
        })

    return pd.DataFrame(results)


def get_volatility_squeeze_signals_from_archive(squeeze_lookback=10, squeeze_percentile=25,
                                                    range_lookback=5, stop_points=40, target_points=80,
                                                    entry_time="08:30", data_folder="data/raw_nq_extended"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
    history["date"] = history.index.date

    session_bars = history[
        (history.index.time >= pd.Timestamp(entry_time).time())
        & (history.index.time <= pd.Timestamp("16:00").time())
    ]
    daily = session_bars.groupby("date").agg(
        high=("High", "max"), low=("Low", "min"), close=("Close", "last")
    )
    daily = daily.sort_index()
    daily["range"] = daily["high"] - daily["low"]

    daily["range_percentile"] = daily["range"].rolling(squeeze_lookback).apply(
        lambda x: (x.iloc[-1] <= x.quantile(squeeze_percentile / 100)) * 100
    )
    daily["was_squeeze"] = daily["range_percentile"].shift(1) == 100

    daily["prior_high"] = daily["high"].rolling(range_lookback).max().shift(1)
    daily["prior_low"] = daily["low"].rolling(range_lookback).min().shift(1)

    opens = history[history.index.time == pd.Timestamp(entry_time).time()].copy()
    opens = opens.join(daily[["was_squeeze", "prior_high", "prior_low"]], on="date")

    def get_signal(row):
        if not row.get("was_squeeze", False):
            return "NONE"
        if pd.isna(row["prior_high"]) or pd.isna(row["prior_low"]):
            return "NONE"
        if row["Close"] > row["prior_high"]:
            return "LONG"
        elif row["Close"] < row["prior_low"]:
            return "SHORT"
        else:
            return "NONE"

    opens["signal"] = opens.apply(get_signal, axis=1)
    signals_only = opens[opens["signal"] != "NONE"].copy()

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
        final_close = day_bars.iloc[-1]["Close"] if len(day_bars) > 0 else entry_price
        return pd.Series({"exit_price": final_close, "exit_reason": "eod"})

    if len(signals_only) == 0:
        signals_only["exit_price"] = pd.Series(dtype="float64")
        signals_only["exit_reason"] = pd.Series(dtype="object")
    else:
        exit_info = signals_only.apply(simulate_trade, axis=1)
        signals_only["exit_price"] = exit_info["exit_price"]
        signals_only["exit_reason"] = exit_info["exit_reason"]

    return signals_only[["date", "signal", "Close", "exit_price", "exit_reason"]]


def get_day_of_week_signals_from_archive(target_day="Wednesday", data_folder="data/raw_nq_extended"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
    history["date"] = history.index.date

    daily = history.groupby("date").agg(open=("Open", "first"), close=("Close", "last"))
    daily.index = pd.to_datetime(daily.index)
    daily = daily.sort_index()
    daily["day_of_week"] = daily.index.day_name()

    target_rows = daily[daily["day_of_week"] == target_day].copy()

    results = []
    for day, row in target_rows.iterrows():
        results.append({
            "date": day.date(), "signal": "LONG",
            "entry_price": row["open"], "exit_price": row["close"],
            "exit_reason": "day_close"
        })

    return pd.DataFrame(results)


def get_day_of_week_stop_signals_from_archive(target_day="Wednesday", stop_points=100, data_folder="data/raw_nq_extended"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
    history["date"] = history.index.date

    daily_dates = pd.DataFrame(index=pd.to_datetime(sorted(history["date"].unique())))
    daily_dates["day_of_week"] = daily_dates.index.day_name()
    target_dates = [d.date() for d in daily_dates[daily_dates["day_of_week"] == target_day].index]

    results = []
    for day in target_dates:
        day_bars = history[history["date"] == day].sort_index()
        if day_bars.empty:
            continue

        entry_price = day_bars.iloc[0]["Open"]
        stop_price = entry_price - stop_points

        exit_price = None
        exit_reason = None
        for _, bar in day_bars.iterrows():
            if bar["Low"] <= stop_price:
                exit_price, exit_reason = stop_price, "stop"
                break

        if exit_price is None:
            exit_price = day_bars.iloc[-1]["Close"]
            exit_reason = "day_close"

        results.append({
            "date": day, "signal": "LONG",
            "entry_price": entry_price, "exit_price": exit_price,
            "exit_reason": exit_reason
        })

    return pd.DataFrame(results)


def get_lead_lag_signals_from_archive(lookback_bars=1, threshold_pct=0.15, hold_bars=1,
                                        nq_folder="data/raw_nq_extended", es_folder="data/raw_es_extended"):
    def load_15m(files):
        all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
        hist = pd.concat(all_days)
        hist = hist[~hist.index.duplicated(keep="first")]
        hist = hist.sort_index()
        hist.index = pd.to_datetime(hist.index, utc=True).tz_convert("America/New_York")
        return hist

    nq_files = glob.glob(os.path.join(nq_folder, "*.csv"))
    es_files = glob.glob(os.path.join(es_folder, "*.csv"))
    if not nq_files or not es_files:
        raise FileNotFoundError("Missing NQ or ES archive data.")

    nq = load_15m(nq_files)[["Close"]].rename(columns={"Close": "nq_close"})
    es = load_15m(es_files)[["Close"]].rename(columns={"Close": "es_close"})

    merged = nq.join(es, how="inner")
    merged["date"] = merged.index.date

    merged["es_return_pct"] = merged["es_close"].pct_change(lookback_bars) * 100
    merged["nq_return_pct"] = merged["nq_close"].pct_change(lookback_bars) * 100

    session_bars = merged[
        (merged.index.time >= pd.Timestamp("08:30").time())
        & (merged.index.time <= pd.Timestamp("15:30").time())
    ].copy()

    results = []
    for day, group in session_bars.groupby("date"):
        group = group.reset_index()
        for i in range(len(group) - hold_bars):
            row = group.iloc[i]
            if pd.isna(row["es_return_pct"]):
                continue

            if row["es_return_pct"] > threshold_pct:
                signal = "LONG"
            elif row["es_return_pct"] < -threshold_pct:
                signal = "SHORT"
            else:
                continue

            entry_price = row["nq_close"]
            exit_price = group.iloc[i + hold_bars]["nq_close"]

            results.append({
                "date": day, "signal": signal,
                "entry_price": entry_price, "exit_price": exit_price,
                "exit_reason": "time_exit"
            })

    return pd.DataFrame(results)


def get_generic_pairs_signals_from_archive(symbol_a_folder, symbol_b_folder, point_value_a, point_value_b,
                                             lookback=20, entry_z=2.0, exit_z=0.5, stop_z=3.5, max_hold_days=15):
    a_files = glob.glob(os.path.join(symbol_a_folder, "*.csv"))
    b_files = glob.glob(os.path.join(symbol_b_folder, "*.csv"))
    if not a_files or not b_files:
        raise FileNotFoundError(f"Missing data in {symbol_a_folder} or {symbol_b_folder}.")

    def load_daily_closes(files):
        all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
        hist = pd.concat(all_days)
        hist = hist[~hist.index.duplicated(keep="first")]
        hist = hist.sort_index()
        hist.index = pd.to_datetime(hist.index, utc=True).tz_convert("America/New_York")
        hist["date"] = hist.index.date
        return hist.groupby("date").agg(close=("Close", "last"))

    a_daily = load_daily_closes(a_files)
    b_daily = load_daily_closes(b_files)

    merged = a_daily.join(b_daily, lsuffix="_a", rsuffix="_b", how="inner")
    merged = merged.sort_index()
    merged["ratio"] = merged["close_a"] / merged["close_b"]
    merged["ratio_mean"] = merged["ratio"].rolling(lookback).mean()
    merged["ratio_std"] = merged["ratio"].rolling(lookback).std()
    merged["zscore"] = (merged["ratio"] - merged["ratio_mean"]) / merged["ratio_std"]
    merged["prior_zscore"] = merged["zscore"].shift(1)

    trading_days = merged.index.tolist()
    results = []
    i = 0
    while i < len(trading_days) - 1:
        day = trading_days[i]
        row = merged.loc[day]
        if pd.isna(row["prior_zscore"]):
            i += 1
            continue

        if row["prior_zscore"] > entry_z:
            direction_a, direction_b = "SHORT", "LONG"
        elif row["prior_zscore"] < -entry_z:
            direction_a, direction_b = "LONG", "SHORT"
        else:
            i += 1
            continue

        entry_day_idx = i
        entry_day = trading_days[entry_day_idx]
        entry_a = merged.loc[entry_day, "close_a"]
        entry_b = merged.loc[entry_day, "close_b"]
        hedge_ratio = (entry_a * point_value_a) / (entry_b * point_value_b)

        exit_day = None
        exit_reason = None
        j = entry_day_idx
        while j < len(trading_days) and j < entry_day_idx + max_hold_days:
            check_day = trading_days[j]
            check_z = merged.loc[check_day, "zscore"]
            if pd.isna(check_z):
                j += 1
                continue
            if direction_a == "SHORT" and check_z <= exit_z:
                exit_day, exit_reason = check_day, "reverted"
                break
            elif direction_a == "LONG" and check_z >= -exit_z:
                exit_day, exit_reason = check_day, "reverted"
                break
            elif direction_a == "SHORT" and check_z >= stop_z:
                exit_day, exit_reason = check_day, "stop"
                break
            elif direction_a == "LONG" and check_z <= -stop_z:
                exit_day, exit_reason = check_day, "stop"
                break
            j += 1

        if exit_day is None:
            exit_day = trading_days[min(j, len(trading_days) - 1)]
            exit_reason = "max_hold"

        exit_a = merged.loc[exit_day, "close_a"]
        exit_b = merged.loc[exit_day, "close_b"]

        pnl_a = (exit_a - entry_a) * point_value_a * (1 if direction_a == "LONG" else -1)
        pnl_b = (exit_b - entry_b) * point_value_b * hedge_ratio * (1 if direction_b == "LONG" else -1)
        total_pnl = pnl_a + pnl_b

        results.append({
            "entry_date": entry_day, "exit_date": exit_day,
            "direction_a": direction_a, "direction_b": direction_b,
            "entry_zscore": row["prior_zscore"], "exit_reason": exit_reason,
            "days_held": j - entry_day_idx, "pnl_dollars": total_pnl
        })
        i = j + 1

    return pd.DataFrame(results)


def get_generic_pairs_signals_from_archive(symbol_a_folder, symbol_b_folder, point_value_a, point_value_b,
                                             lookback=20, entry_z=2.0, exit_z=0.5, stop_z=3.5, max_hold_days=15):
    a_files = glob.glob(os.path.join(symbol_a_folder, "*.csv"))
    b_files = glob.glob(os.path.join(symbol_b_folder, "*.csv"))
    if not a_files or not b_files:
        raise FileNotFoundError(f"Missing data in {symbol_a_folder} or {symbol_b_folder}.")

    def load_daily_closes(files):
        all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
        hist = pd.concat(all_days)
        hist = hist[~hist.index.duplicated(keep="first")]
        hist = hist.sort_index()
        hist.index = pd.to_datetime(hist.index, utc=True).tz_convert("America/New_York")
        hist["date"] = hist.index.date
        return hist.groupby("date").agg(close=("Close", "last"))

    a_daily = load_daily_closes(a_files)
    b_daily = load_daily_closes(b_files)

    merged = a_daily.join(b_daily, lsuffix="_a", rsuffix="_b", how="inner")
    merged = merged.sort_index()
    merged["ratio"] = merged["close_a"] / merged["close_b"]
    merged["ratio_mean"] = merged["ratio"].rolling(lookback).mean()
    merged["ratio_std"] = merged["ratio"].rolling(lookback).std()
    merged["zscore"] = (merged["ratio"] - merged["ratio_mean"]) / merged["ratio_std"]
    merged["prior_zscore"] = merged["zscore"].shift(1)

    trading_days = merged.index.tolist()
    results = []
    i = 0
    while i < len(trading_days) - 1:
        day = trading_days[i]
        row = merged.loc[day]
        if pd.isna(row["prior_zscore"]):
            i += 1
            continue

        if row["prior_zscore"] > entry_z:
            direction_a, direction_b = "SHORT", "LONG"
        elif row["prior_zscore"] < -entry_z:
            direction_a, direction_b = "LONG", "SHORT"
        else:
            i += 1
            continue

        entry_day_idx = i
        entry_day = trading_days[entry_day_idx]
        entry_a = merged.loc[entry_day, "close_a"]
        entry_b = merged.loc[entry_day, "close_b"]
        hedge_ratio = (entry_a * point_value_a) / (entry_b * point_value_b)

        exit_day = None
        exit_reason = None
        j = entry_day_idx
        while j < len(trading_days) and j < entry_day_idx + max_hold_days:
            check_day = trading_days[j]
            check_z = merged.loc[check_day, "zscore"]
            if pd.isna(check_z):
                j += 1
                continue
            if direction_a == "SHORT" and check_z <= exit_z:
                exit_day, exit_reason = check_day, "reverted"
                break
            elif direction_a == "LONG" and check_z >= -exit_z:
                exit_day, exit_reason = check_day, "reverted"
                break
            elif direction_a == "SHORT" and check_z >= stop_z:
                exit_day, exit_reason = check_day, "stop"
                break
            elif direction_a == "LONG" and check_z <= -stop_z:
                exit_day, exit_reason = check_day, "stop"
                break
            j += 1

        if exit_day is None:
            exit_day = trading_days[min(j, len(trading_days) - 1)]
            exit_reason = "max_hold"

        exit_a = merged.loc[exit_day, "close_a"]
        exit_b = merged.loc[exit_day, "close_b"]

        pnl_a = (exit_a - entry_a) * point_value_a * (1 if direction_a == "LONG" else -1)
        pnl_b = (exit_b - entry_b) * point_value_b * hedge_ratio * (1 if direction_b == "LONG" else -1)
        total_pnl = pnl_a + pnl_b

        results.append({
            "entry_date": entry_day, "exit_date": exit_day,
            "direction_a": direction_a, "direction_b": direction_b,
            "entry_zscore": row["prior_zscore"], "exit_reason": exit_reason,
            "days_held": j - entry_day_idx, "pnl_dollars": total_pnl
        })
        i = j + 1

    return pd.DataFrame(results)


def get_overnight_reversion_signals_from_archive(min_move_points=50, stop_points=40, target_points=60,
                                                     entry_time="08:30", data_folder="data/raw_nq_extended"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
    history["date"] = history.index.date

    def get_price_at_time(target_date, target_time):
        day_data = history[history["date"] == target_date]
        bar = day_data[day_data.index.time == target_time]
        return bar.iloc[0]["Close"] if not bar.empty else None

    overnight_start_time = pd.Timestamp("19:00").time()
    entry_t = pd.Timestamp(entry_time).time()

    unique_dates = sorted(history["date"].unique())
    results = []

    for i in range(1, len(unique_dates)):
        today = unique_dates[i]
        prior_day = unique_dates[i - 1]

        overnight_start_price = get_price_at_time(prior_day, overnight_start_time)
        entry_price = get_price_at_time(today, entry_t)

        if overnight_start_price is None or entry_price is None:
            continue

        overnight_move = entry_price - overnight_start_price

        if abs(overnight_move) < min_move_points:
            continue

        signal = "SHORT" if overnight_move > 0 else "LONG"

        if signal == "LONG":
            stop_price = entry_price - stop_points
            target_price = entry_price + target_points
        else:
            stop_price = entry_price + stop_points
            target_price = entry_price - target_points

        day_bars = history[
            (history["date"] == today)
            & (history.index.time > entry_t)
            & (history.index.time <= pd.Timestamp("16:00").time())
        ]

        exit_price = None
        exit_reason = None
        for _, bar in day_bars.iterrows():
            if signal == "LONG":
                hit_stop = bar["Low"] <= stop_price
                hit_target = bar["High"] >= target_price
            else:
                hit_stop = bar["High"] >= stop_price
                hit_target = bar["Low"] <= target_price
            if hit_stop:
                exit_price, exit_reason = stop_price, "stop"
                break
            elif hit_target:
                exit_price, exit_reason = target_price, "target"
                break

        if exit_price is None:
            exit_price = day_bars.iloc[-1]["Close"] if len(day_bars) > 0 else entry_price
            exit_reason = "eod"

        results.append({
            "date": today, "signal": signal, "overnight_move": overnight_move,
            "entry_price": entry_price, "exit_price": exit_price, "exit_reason": exit_reason
        })

    return pd.DataFrame(results)


def check_cointegration(symbol_a_folder, symbol_b_folder, label="A/B", in_sample_frac=0.7):
    """Engle-Granger cointegration test on daily log-closes, computed on the IN-SAMPLE portion
    only (first in_sample_frac of the overlapping history) to avoid look-ahead. This answers
    'is there real statistical evidence these two series share a long-run equilibrium', which a
    rolling z-score of their ratio does NOT prove on its own - a rolling window will make almost
    any two series look mean-reverting around their own rolling mean by construction. Requires
    statsmodels; prints an install instruction and returns None if it isn't available rather
    than failing the whole script."""
    try:
        from statsmodels.tsa.stattools import coint
    except ImportError:
        print(f"[{label}] statsmodels not installed - skipping cointegration test. "
              f"Install with: pip install statsmodels")
        return None

    import numpy as np

    a_files = glob.glob(os.path.join(symbol_a_folder, "*.csv"))
    b_files = glob.glob(os.path.join(symbol_b_folder, "*.csv"))
    if not a_files or not b_files:
        raise FileNotFoundError(f"Missing data in {symbol_a_folder} or {symbol_b_folder}.")

    def load_daily_closes(files):
        all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
        hist = pd.concat(all_days)
        hist = hist[~hist.index.duplicated(keep="first")]
        hist = hist.sort_index()
        hist.index = pd.to_datetime(hist.index, utc=True).tz_convert("America/New_York")
        hist["date"] = hist.index.date
        return hist.groupby("date").agg(close=("Close", "last"))

    a_daily = load_daily_closes(a_files)
    b_daily = load_daily_closes(b_files)
    merged = a_daily.join(b_daily, lsuffix="_a", rsuffix="_b", how="inner").sort_index()

    n = len(merged)
    split = int(n * in_sample_frac)
    in_sample = merged.iloc[:split]

    log_a = np.log(in_sample["close_a"])
    log_b = np.log(in_sample["close_b"])

    score, pvalue, crit_values = coint(log_a, log_b)

    print(f"[{label}] Engle-Granger cointegration test, in-sample only ({len(in_sample)} of {n} days, "
          f"{in_sample.index.min()} to {in_sample.index.max()}):")
    print(f"  Test statistic: {score:.4f}")
    print(f"  p-value: {pvalue:.4f}")
    print(f"  Critical values (1%/5%/10%): {crit_values[0]:.4f} / {crit_values[1]:.4f} / {crit_values[2]:.4f}")
    if pvalue < 0.05:
        print(f"  -> Cointegrated at 5% significance. Statistical evidence supports a genuine long-run relationship.")
    else:
        print(f"  -> NOT cointegrated at 5% significance. The rolling z-score reversion could be a rolling-window")
        print(f"     artifact rather than a real, durable relationship - treat live results with extra caution.")

    return {"label": label, "score": score, "pvalue": pvalue, "crit_values": crit_values, "n_days": len(in_sample)}


def get_overnight_drift_signals_from_archive(data_folder="data/raw_nq_extended", entry_time="08:30",
                                                session_close_time="16:00", direction="LONG"):
    """Unconditional overnight hold: enter at the prior day's regular-session close, exit at
    today's regular-session open. No gap-size filter, no price-pattern condition - this tests
    the pure calendar-based hypothesis that overnight session drift is systematically positive
    (or negative), distinct from get_gap_signals_from_archive (which trades AFTER the open based
    on gap size) and get_overnight_reversion_signals_from_archive (which only fires on unusually
    large overnight moves and bets on partial reversal during the day)."""
    files = glob.glob(os.path.join(data_folder, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
    history["date"] = history.index.date

    def get_price_at_time(target_date, target_time):
        day_data = history[history["date"] == target_date]
        bar = day_data[day_data.index.time == target_time]
        return bar.iloc[0]["Close"] if not bar.empty else None

    close_t = pd.Timestamp(session_close_time).time()
    entry_t = pd.Timestamp(entry_time).time()

    unique_dates = sorted(history["date"].unique())
    results = []

    for i in range(1, len(unique_dates)):
        today = unique_dates[i]
        prior_day = unique_dates[i - 1]

        prior_close = get_price_at_time(prior_day, close_t)
        todays_open_bar = history[(history["date"] == today) & (history.index.time == entry_t)]

        if prior_close is None or todays_open_bar.empty:
            continue

        entry_price = prior_close
        exit_price = todays_open_bar.iloc[0]["Open"]

        results.append({
            "entry_date": prior_day, "exit_date": today, "signal": direction,
            "entry_price": entry_price, "exit_price": exit_price,
        })

    return pd.DataFrame(results)


def get_gap_signals_with_volume_from_archive(min_gap_points=30, stop_points=40, target_points=80,
                                                volume_lookback=20, data_folder="data/raw_nq_extended"):
    """Same continuation-mode gap signal as get_gap_signals_from_archive, but also captures the
    opening 15-min bar's volume and its ratio to the trailing volume_lookback-day average of that
    same bar, so a research script can test whether above-average opening participation changes
    the existing gap-continuation edge. NOT a substitute for real order-flow / tick data - this
    dataset only has OHLCV bars, so this can only measure total bar volume, not buy/sell
    aggressor imbalance (that would need a different, likely paid, Databento schema)."""
    files = glob.glob(os.path.join(data_folder, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
    history["date"] = history.index.date

    daily = history.groupby("date").agg(
        open=("Open", "first"), high=("High", "max"),
        low=("Low", "min"), close=("Close", "last")
    )
    daily = daily.sort_index()
    daily["prior_close"] = daily["close"].shift(1)
    daily["gap_points"] = daily["open"] - daily["prior_close"]

    open_time = pd.Timestamp("08:30").time()
    open_bars = history[history.index.time == open_time].groupby("date")["Volume"].first().rename("open_volume")
    daily = daily.join(open_bars, how="left")
    # min_periods matters here: ~17% of days are missing an exact 08:30 bar, so rolling()'s
    # default min_periods=window would require ALL 20 days in the window to be non-null -
    # almost never true - collapsing open_volume_avg (and everything downstream) to NaN.
    # Half the window present is enough for a usable trailing average.
    daily["open_volume_avg"] = daily["open_volume"].rolling(
        volume_lookback, min_periods=max(5, volume_lookback // 2)
    ).mean().shift(1)
    daily["volume_ratio"] = daily["open_volume"] / daily["open_volume_avg"]

    results = []
    trading_days = daily.index.tolist()

    for day in trading_days:
        row = daily.loc[day]
        if pd.isna(row["gap_points"]) or pd.isna(row["volume_ratio"]):
            continue
        if abs(row["gap_points"]) < min_gap_points:
            continue

        gap_up = row["gap_points"] > 0
        signal = "LONG" if gap_up else "SHORT"  # continuation mode, matching the live gap strategy

        entry_price = row["open"]
        if signal == "LONG":
            stop_price = entry_price - stop_points
            target_price = entry_price + target_points
        else:
            stop_price = entry_price + stop_points
            target_price = entry_price - target_points

        day_bars = history[
            (history["date"] == day)
            & (history.index.time > open_time)
            & (history.index.time <= pd.Timestamp("16:00").time())
        ]

        exit_price = None
        exit_reason = None
        for _, bar in day_bars.iterrows():
            if signal == "LONG":
                hit_stop = bar["Low"] <= stop_price
                hit_target = bar["High"] >= target_price
            else:
                hit_stop = bar["High"] >= stop_price
                hit_target = bar["Low"] <= target_price
            if hit_stop:
                exit_price, exit_reason = stop_price, "stop"
                break
            elif hit_target:
                exit_price, exit_reason = target_price, "target"
                break

        if exit_price is None:
            exit_price = day_bars.iloc[-1]["Close"] if len(day_bars) > 0 else row["close"]
            exit_reason = "eod"

        results.append({
            "date": day, "signal": signal, "gap_points": row["gap_points"],
            "entry_price": entry_price, "exit_price": exit_price, "exit_reason": exit_reason,
            "volume_ratio": row["volume_ratio"],
        })

    return pd.DataFrame(results)


def get_weekday_open_gap_signals_from_archive(min_gap_points=30, stop_points=40, target_points=80,
                                                 entry_time="08:30", session_end="16:00",
                                                 data_folder="data/raw_nq_extended"):
    """IMPORTANT: get_gap_signals_from_archive() defines 'open' as the FIRST bar of the calendar
    date (via groupby("date").agg(open=("Open","first"))). For a Sunday, the first bar of that
    date is the 6PM Globex reopen - so its "gap" is really the Friday-close-to-Sunday-reopen
    weekend gap, not an intraday open-bell gap. Investigation on 2026-09-09 found that ALL 70 of
    Entry 10's trades are exactly this: 68 Sundays + 2 anomalies, and every single one exits via
    "eod" (session close) because a Sunday date has no 08:30-16:00 RTH bars at all - the
    stop_points/target_points parameters are never actually invoked for any of the 70 trades.

    This function instead defines the gap the way the LIVE script (gap_forward_check.py) actually
    does: entry_time bar's Open vs. the prior trading day's close, restricted to days that
    actually HAVE an entry_time bar (which structurally excludes Sunday, since Sunday has no
    08:30 ET bar) - so this tests the strategy that is actually running live, not the Sunday-
    reopen effect that produced Entry 10's PF 2.57. See research_log.md Entry 16 for the
    corrected backtest results (PF 1.22, 468 trades, 4/5 scorecard - meaningfully different from
    Entry 10)."""
    files = glob.glob(os.path.join(data_folder, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No archive files found in {data_folder}.")

    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
    history["date"] = history.index.date

    entry_t = pd.Timestamp(entry_time).time()
    close_t = pd.Timestamp(session_end).time()

    daily_close = history.groupby("date").agg(close=("Close", "last")).sort_index()
    daily_close["prior_close"] = daily_close["close"].shift(1)

    entry_bars = history[history.index.time == entry_t].groupby("date")["Open"].first().rename("entry_open")
    daily = daily_close.join(entry_bars, how="inner")  # inner: only days that actually have an entry_time bar
    daily["gap_points"] = daily["entry_open"] - daily["prior_close"]

    results = []
    for day in daily.index.tolist():
        row = daily.loc[day]
        if pd.isna(row["gap_points"]) or abs(row["gap_points"]) < min_gap_points:
            continue

        gap_up = row["gap_points"] > 0
        signal = "LONG" if gap_up else "SHORT"  # continuation mode, matching the live gap strategy

        entry_price = row["entry_open"]
        if signal == "LONG":
            stop_price = entry_price - stop_points
            target_price = entry_price + target_points
        else:
            stop_price = entry_price + stop_points
            target_price = entry_price - target_points

        day_bars = history[
            (history["date"] == day)
            & (history.index.time > entry_t)
            & (history.index.time <= close_t)
        ]

        exit_price = None
        exit_reason = None
        for _, bar in day_bars.iterrows():
            if signal == "LONG":
                hit_stop = bar["Low"] <= stop_price
                hit_target = bar["High"] >= target_price
            else:
                hit_stop = bar["High"] >= stop_price
                hit_target = bar["Low"] <= target_price
            if hit_stop:
                exit_price, exit_reason = stop_price, "stop"
                break
            elif hit_target:
                exit_price, exit_reason = target_price, "target"
                break

        if exit_price is None:
            exit_price = day_bars.iloc[-1]["Close"] if len(day_bars) > 0 else entry_price
            exit_reason = "eod"

        results.append({
            "date": day, "signal": signal, "gap_points": row["gap_points"],
            "entry_price": entry_price, "exit_price": exit_price, "exit_reason": exit_reason
        })

    return pd.DataFrame(results)

