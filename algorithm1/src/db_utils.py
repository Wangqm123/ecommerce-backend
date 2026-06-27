import json
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from typing import Optional, Dict, Any, List
from config import DB_CONFIG


def get_engine() -> Engine:
    """创建数据库引擎"""
    url = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"
    return create_engine(url, pool_pre_ping=True)


def fetch_pending_task(engine: Engine) -> Optional[Dict[str, Any]]:
    """获取一个 pending 状态的预测任务"""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM forecast_tasks WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1")
        )
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None


def update_task_status(engine: Engine, batch_uuid: str, status: str, error_msg: str = None):
    """更新任务状态（注意：表中没有 error_message 字段）"""
    with engine.connect() as conn:
        if status == 'running':
            conn.execute(
                text("UPDATE forecast_tasks SET status = 'running', started_at = NOW() WHERE batch_uuid = :bu"),
                {"bu": batch_uuid}
            )
        elif status == 'completed':
            conn.execute(
                text("UPDATE forecast_tasks SET status = 'completed', completed_at = NOW() WHERE batch_uuid = :bu"),
                {"bu": batch_uuid}
            )
        elif status == 'failed':
            # 表中没有 error_message 字段，只更新状态
            conn.execute(
                text("UPDATE forecast_tasks SET status = 'failed', completed_at = NOW() WHERE batch_uuid = :bu"),
                {"bu": batch_uuid}
            )
        conn.commit()

    # 错误信息只记录到日志，不写入数据库
    if error_msg:
        print(f"[Error] Task {batch_uuid} failed: {error_msg}")


def get_training_data(engine: Engine, start_date: str, end_date: str,
                      product_ids: Optional[List[int]] = None) -> pd.DataFrame:
    """获取历史日销量数据"""
    query = """
            SELECT o.product_id, \
                   p.product_name, \
                   o.order_date, \
                   SUM(o.quantity) AS daily_quantity
            FROM orders o
                     JOIN products p ON o.product_id = p.product_id
            WHERE o.order_status = 'completed'
              AND o.order_date BETWEEN :start AND :end \
            """
    params = {"start": start_date, "end": end_date}

    if product_ids and len(product_ids) > 0:
        placeholders = ','.join([f":pid{i}" for i in range(len(product_ids))])
        query += f" AND o.product_id IN ({placeholders})"
        for i, pid in enumerate(product_ids):
            params[f"pid{i}"] = pid

    query += " GROUP BY o.product_id, p.product_name, o.order_date ORDER BY o.product_id, o.order_date"

    df = pd.read_sql_query(text(query), engine, params=params)
    df['order_date'] = pd.to_datetime(df['order_date'])
    return df


def write_forecast_results(engine: Engine, batch_uuid: str, product_id: int, product_name: str,
                           forecasts_df: pd.DataFrame, model_name: str):
    """将预测结果写入 forecast_results 表"""
    records = []
    for _, row in forecasts_df.iterrows():
        pred_qty = int(row['predicted_qty'])
        lb = int(row['lower_bound']) if pd.notna(row['lower_bound']) and row['lower_bound'] is not None else None
        ub = int(row['upper_bound']) if pd.notna(row['upper_bound']) and row['upper_bound'] is not None else None
        records.append({
            'product_id': product_id,
            'product_name': product_name,
            'forecast_date': row['forecast_date'].date(),
            'predicted_qty': pred_qty,
            'lower_bound': lb,
            'upper_bound': ub,
            'model_name': model_name,
            'compute_batch': batch_uuid
        })
    if records:
        df_result = pd.DataFrame(records)
        df_result.to_sql('forecast_results', engine, if_exists='append', index=False)