import pandas as pd
import numpy as np
from datetime import timedelta
from sklearn.ensemble import IsolationForest

# 尝试导入 Prophet
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    print("Warning: Prophet not installed, using simple forecast.")


# ============================================================
# 异常检测相关函数
# ============================================================

def detect_anomalies(ts_df: pd.DataFrame, contamination: float = 0.05) -> pd.Series:
    """
    使用 Isolation Forest 检测时间序列中的异常点

    参数:
        ts_df: 包含 'daily_quantity' 列的 DataFrame
        contamination: 预期异常比例（默认5%）

    返回:
        is_anomaly: bool Series，True 表示该点为异常
    """
    if len(ts_df) < 14:  # 数据太少，不检测
        return pd.Series([False] * len(ts_df), index=ts_df.index)

    # 提取特征：当前值 + 前7天移动平均 + 前30天移动平均 + 滞后值
    df_features = ts_df.copy()
    df_features['ma_7'] = df_features['daily_quantity'].rolling(7, min_periods=1).mean()
    df_features['ma_30'] = df_features['daily_quantity'].rolling(30, min_periods=1).mean()
    df_features['lag_1'] = df_features['daily_quantity'].shift(1).fillna(df_features['daily_quantity'])
    df_features['lag_7'] = df_features['daily_quantity'].shift(7).fillna(df_features['daily_quantity'])

    feature_cols = ['daily_quantity', 'ma_7', 'ma_30', 'lag_1', 'lag_7']
    X = df_features[feature_cols].values

    # 使用 Isolation Forest 检测异常
    iso_forest = IsolationForest(contamination=contamination, random_state=42)
    predictions = iso_forest.fit_predict(X)

    # -1 表示异常
    is_anomaly = predictions == -1
    return is_anomaly


def fix_anomalies(ts_df: pd.DataFrame, is_anomaly: pd.Series) -> pd.DataFrame:
    """
    修正异常值：用前后7天的中位数替换
    """
    df_fixed = ts_df.copy()

    for idx in df_fixed.index[is_anomaly]:
        # 取前后7天的值
        pos = df_fixed.index.get_loc(idx)
        start = max(0, pos - 7)
        end = min(len(df_fixed), pos + 8)
        surrounding = df_fixed.iloc[start:end]['daily_quantity'].values
        # 排除自身，取中位数
        median_val = np.median([v for v in surrounding if v != df_fixed.loc[idx, 'daily_quantity']])
        df_fixed.loc[idx, 'daily_quantity'] = int(round(median_val))

    return df_fixed


def apply_anomaly_detection(ts_df: pd.DataFrame, enable: bool = True, contamination: float = 0.05) -> pd.DataFrame:
    """
    对时间序列应用异常检测和修正

    参数:
        ts_df: 包含 'daily_quantity' 列的 DataFrame
        enable: 是否启用异常检测
        contamination: 异常比例

    返回:
        修正后的 DataFrame
    """
    if not enable or len(ts_df) < 14:
        return ts_df

    is_anomaly = detect_anomalies(ts_df, contamination)
    if is_anomaly.sum() > 0:
        df_fixed = fix_anomalies(ts_df, is_anomaly)
        print(f"Detected and fixed {is_anomaly.sum()} anomalies")
        return df_fixed

    return ts_df


# ============================================================
# 预测主函数
# ============================================================

def forecast_for_product(ts_df: pd.DataFrame, forecast_days: int,
                         model_name: str = 'prophet',
                         use_holidays: bool = True,
                         use_anomaly_detection: bool = True,
                         holidays_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    对单个商品的时间序列进行预测

    参数:
        ts_df: DataFrame 必须包含 'order_date' 和 'daily_quantity' 列
        forecast_days: 预测天数
        model_name: 'prophet' 或 'arima' 或 'simple'
        use_holidays: 是否使用节假日特征
        use_anomaly_detection: 是否使用异常检测预处理
        holidays_df: 节假日 DataFrame（需要包含 ds 和 holiday 列）

    返回:
        DataFrame 包含列: forecast_date, predicted_qty, lower_bound, upper_bound
    """
    # 确保日期连续，缺失日期填充0
    ts_df = ts_df.sort_values('order_date')
    ts_df = ts_df.set_index('order_date').asfreq('D', fill_value=0).reset_index()
    ts_df.columns = ['order_date', 'daily_quantity']

    # 异常检测预处理
    if use_anomaly_detection:
        ts_df = apply_anomaly_detection(ts_df, enable=True)

    # 数据太少（<7天）直接使用移动平均
    if len(ts_df) < 7:
        return _simple_forecast(ts_df, forecast_days)

    # 根据模型选择
    if model_name == 'prophet' and PROPHET_AVAILABLE:
        try:
            return _prophet_forecast(ts_df, forecast_days, use_holidays, holidays_df)
        except Exception as e:
            print(f"Prophet failed with error: {e}, falling back to simple forecast.")
            return _simple_forecast(ts_df, forecast_days)
    else:
        return _simple_forecast(ts_df, forecast_days)


# ============================================================
# 内部预测函数
# ============================================================

def _prophet_forecast(ts_df: pd.DataFrame, forecast_days: int,
                      use_holidays: bool = True,
                      holidays_df: pd.DataFrame = None) -> pd.DataFrame:
    """使用 Prophet 模型预测，支持节假日特征"""
    df_prophet = ts_df.rename(columns={'order_date': 'ds', 'daily_quantity': 'y'})

    # 检查数据是否方差太小（全零或常数）
    if df_prophet['y'].std() < 0.1:
        return _simple_forecast(ts_df, forecast_days)

    # 创建 Prophet 模型（放在 try 块内部）
    try:
        if use_holidays and holidays_df is not None and not holidays_df.empty:
            holidays_copy = holidays_df.copy()
            holidays_copy['ds'] = pd.to_datetime(holidays_copy['ds'])
            model = Prophet(interval_width=0.95, daily_seasonality=True, holidays=holidays_copy)
        else:
            model = Prophet(interval_width=0.95, daily_seasonality=True)
    except Exception as e:
        print(f"Prophet initialization failed: {e}")
        return _simple_forecast(ts_df, forecast_days)

    try:
        model.fit(df_prophet)
        future = model.make_future_dataframe(periods=forecast_days)
        forecast = model.predict(future)
        result = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(forecast_days)
        result.columns = ['forecast_date', 'predicted_qty', 'lower_bound', 'upper_bound']
        result['predicted_qty'] = result['predicted_qty'].clip(lower=0).round().astype(int)
        result['lower_bound'] = result['lower_bound'].clip(lower=0).round().astype(int)
        result['upper_bound'] = result['upper_bound'].clip(lower=0).round().astype(int)
        return result
    except Exception as e:
        print(f"Prophet fitting/prediction failed: {e}")
        return _simple_forecast(ts_df, forecast_days)


def _simple_forecast(ts_df: pd.DataFrame, forecast_days: int) -> pd.DataFrame:
    """简单移动平均预测（兜底方案）"""
    last_avg = ts_df['daily_quantity'].tail(7).mean()
    last_date = ts_df['order_date'].max()
    forecast_dates = pd.date_range(last_date + timedelta(days=1), periods=forecast_days)
    predicted = max(0, int(round(last_avg)))
    result = pd.DataFrame({
        'forecast_date': forecast_dates,
        'predicted_qty': [predicted] * forecast_days,
        'lower_bound': [None] * forecast_days,
        'upper_bound': [None] * forecast_days
    })
    return result