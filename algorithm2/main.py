"""
算法2 — RFM 用户分群 主程序
支持两种运行模式：

用法:
    python main.py              # 前台运行，持续轮询
    python main.py --once       # 单次处理一个 pending 任务后退出
    python main.py --batch-uuid <uuid>  # 指定处理某个任务
    python main.py --server     # HTTP 服务模式（自带后台轮询）
"""
import argparse
import json
import logging
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pymysql
from flask import Flask, jsonify
from pymysql.cursors import DictCursor

from config import DB_CONFIG, POLL_INTERVAL, MAX_BATCH_TASKS, DEFAULT_SCORING_METHOD, LOG_LEVEL
from rfm_engine import RFMEngine, RFMResult, RFMSummary

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rfm_main")


# ===================================================================
# 数据库工具
# ===================================================================

def get_connection() -> pymysql.Connection:
    """创建 MySQL 连接（autocommit 模式）。"""
    conn = pymysql.connect(**DB_CONFIG, cursorclass=DictCursor)
    conn.autocommit(True)
    return conn


def fetch_pending_tasks(cursor, limit: int = 1) -> List[Dict[str, Any]]:
    """查找状态为 pending 的任务，按创建时间排序。"""
    cursor.execute(
        "SELECT * FROM rfm_compute_tasks WHERE status = 'pending' "
        "ORDER BY created_at ASC LIMIT %s",
        (limit,),
    )
    return cursor.fetchall()


def fetch_task_by_uuid(cursor, batch_uuid: str) -> Optional[Dict[str, Any]]:
    cursor.execute(
        "SELECT * FROM rfm_compute_tasks WHERE batch_uuid = %s",
        (batch_uuid,),
    )
    return cursor.fetchone()


def update_task_status(cursor, batch_uuid: str, status: str, **extra) -> None:
    """更新任务状态与附加字段。"""
    allowed = {"running", "completed", "failed"}
    if status not in allowed:
        raise ValueError(f"状态值非法: {status}，允许 {allowed}")

    sets = ["status = %s"]
    params: List[Any] = [status]

    if status == "running":
        sets.append("started_at = NOW()")
    elif status in ("completed", "failed"):
        sets.append("completed_at = NOW()")

    for col, val in extra.items():
        sets.append(f"{col} = %s")
        params.append(val)

    params.append(batch_uuid)
    sql = f"UPDATE rfm_compute_tasks SET {', '.join(sets)} WHERE batch_uuid = %s"
    cursor.execute(sql, params)


def fetch_order_data(
    cursor, start_date: str, end_date: str
) -> pd.DataFrame:
    """
    查询订单数据，返回包含 user_id, order_id, order_date, total_amount 的 DataFrame。

    优先使用视图 v_rfm_input；若视图不存在则直接查询 orders 表。
    """
    # 尝试视图
    try:
        cursor.execute(
            "SELECT user_id, order_id, order_date, total_amount "
            "FROM v_rfm_input "
            "WHERE order_date BETWEEN %s AND %s AND order_status = 'completed'",
            (start_date, end_date),
        )
        rows = cursor.fetchall()
        if rows:
            logger.info("通过视图 v_rfm_input 获取 %d 行订单数据", len(rows))
            return pd.DataFrame(rows)
    except Exception:
        logger.debug("视图 v_rfm_input 不可用，回退到直接查询 orders 表")

    # 直接查询
    sql = (
        "SELECT user_id, order_id, order_date, total_amount "
        "FROM orders "
        "WHERE order_status = 'completed' "
        "  AND order_date BETWEEN %s AND %s"
    )
    cursor.execute(sql, (start_date, end_date))
    rows = cursor.fetchall()
    logger.info("通过 orders 表获取 %d 行订单数据", len(rows))
    return pd.DataFrame(rows)


def insert_results(cursor, results: List[RFMResult], compute_batch: str) -> int:
    """批量写入 rfm_results 表。返回写入行数。"""
    if not results:
        return 0

    sql = (
        "INSERT INTO rfm_results "
        "(user_id, recency, frequency, monetary, r_score, f_score, m_score, "
        "rfm_segment, rfm_group, compute_batch) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    rows = [r.to_db_row(compute_batch) for r in results]
    cursor.executemany(sql, rows)
    logger.info("写入 rfm_results %d 行", len(rows))
    return len(rows)


def clear_previous_results(cursor, compute_batch: str) -> int:
    """删除同一批次的旧结果（幂等写入）。"""
    cursor.execute(
        "DELETE FROM rfm_results WHERE compute_batch = %s",
        (compute_batch,),
    )
    return cursor.rowcount


# ===================================================================
# 任务执行
# ===================================================================

def parse_task_params(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析任务参数。
    params 字段为 JSON 字符串，包含 startDate, endDate, recencyBaseDate, scoringMethod 等。
    """
    raw = task.get("params", "{}")
    if isinstance(raw, str):
        try:
            params = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            params = {}
    elif isinstance(raw, dict):
        params = raw
    else:
        params = {}

    return {
        "start_date": params.get("startDate", "2025-01-01"),
        "end_date": params.get("endDate", "2025-12-31"),
        "recency_base_date": params.get("recencyBaseDate", params.get("endDate", "2025-12-31")),
        "scoring_method": params.get("scoringMethod", DEFAULT_SCORING_METHOD),
    }


def compute_previous_period(start_date: str, end_date: str) -> Tuple[str, str]:
    """根据当期起止日期推算上期起止日期（等长窗口）。"""
    fmt = "%Y-%m-%d"
    s = datetime.strptime(start_date, fmt)
    e = datetime.strptime(end_date, fmt)
    period_days = (e - s).days + 1  # +1: BETWEEN 是闭区间
    prev_end = s - timedelta(days=1)
    prev_start = s - timedelta(days=period_days)
    return prev_start.strftime(fmt), prev_end.strftime(fmt)


def execute_task(cursor, task: Dict[str, Any]) -> None:
    """执行单个 RFM 计算任务。"""
    batch_uuid = task["batch_uuid"]
    logger.info("===== 开始执行任务 %s =====", batch_uuid)

    # 1. 标记 running
    update_task_status(cursor, batch_uuid, "running")
    logger.info("任务状态更新为 running")

    try:
        # 2. 解析参数
        p = parse_task_params(task)
        logger.info(
            "任务参数: start=%s end=%s recency_base=%s scoring=%s",
            p["start_date"], p["end_date"],
            p["recency_base_date"], p["scoring_method"],
        )

        # 3. 读取当期订单数据
        df = fetch_order_data(cursor, p["start_date"], p["end_date"])
        if df.empty:
            logger.warning("当期无订单数据，任务以 user_count=0 完成")
            update_task_status(cursor, batch_uuid, "completed", user_count=0)
            return

        df["order_date"] = pd.to_datetime(df["order_date"])
        df["user_id"] = df["user_id"].astype(int)

        # 4. 读取上期订单数据（用于留存率）
        prev_start, prev_end = compute_previous_period(p["start_date"], p["end_date"])
        logger.info("留存率对比窗口: prev=[%s, %s] curr=[%s, %s]",
                    prev_start, prev_end, p["start_date"], p["end_date"])
        try:
            prev_df = fetch_order_data(cursor, prev_start, prev_end)
            if not prev_df.empty:
                prev_df["order_date"] = pd.to_datetime(prev_df["order_date"])
                prev_df["user_id"] = prev_df["user_id"].astype(int)
            else:
                prev_df = None
        except Exception as e:
            logger.warning("上期数据查询失败，跳过留存率计算: %s", e)
            prev_df = None

        # 5. 执行 RFM 全流程
        results, summary = RFMEngine.run(
            df=df,
            recency_base_date=p["recency_base_date"],
            scoring_method=p["scoring_method"],
            prev_df=prev_df,
        )

        # 6. 写入结果表（先清除同批次旧数据实现幂等）
        clear_previous_results(cursor, batch_uuid)
        insert_results(cursor, results, batch_uuid)

        # 7. 打印汇总
        _print_summary(summary)

        # 8. 更新任务状态为完成
        update_task_status(cursor, batch_uuid, "completed", user_count=summary.total_users)
        logger.info("任务 %s 完成，用户数=%d", batch_uuid, summary.total_users)

    except Exception:
        logger.exception("任务 %s 执行异常", batch_uuid)
        try:
            update_task_status(cursor, batch_uuid, "failed")
        except Exception:
            logger.exception("更新失败状态时再次异常")


def _print_summary(s: RFMSummary) -> None:
    """格式化输出汇总指标。"""
    logger.info("=" * 50)
    logger.info("RFM 分析汇总报告")
    logger.info("=" * 50)
    logger.info("总用户数: %d", s.total_users)
    logger.info("复购率:   %.2f%% (%d 人复购)", s.repurchase_rate, s.repurchase_users)
    if s.retention_rate is not None:
        logger.info("留存率:   %.2f%% (%d/%d)", s.retention_rate,
                    s.retention_users, s.previous_period_users)

    logger.info("--- 用户分层 ---")
    for seg, cnt in sorted(s.segment_counts.items(), key=lambda x: -x[1]):
        pct = s.segment_percents.get(seg, 0)
        avg_m = s.segment_avg_monetary.get(seg, 0)
        logger.info("  %s: %d人 (%.1f%%) 均消¥%.2f", seg, cnt, pct, avg_m)

    logger.info("--- 购买力分布 ---")
    order = ["高购买力", "中高购买力", "中购买力", "中低购买力", "低购买力"]
    for tier in order:
        cnt = s.purchasing_power_counts.get(tier, 0)
        if cnt:
            logger.info("  %s: %d人 (%.1f%%)", tier, cnt, cnt / s.total_users * 100)


# ===================================================================
# 主入口
# ===================================================================

def run_loop() -> None:
    """持续轮询 pending 任务并执行。"""
    logger.info("RFM 算法服务启动，轮询间隔=%ds，数据库=%s",
                POLL_INTERVAL, DB_CONFIG["database"])

    while True:
        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                tasks = fetch_pending_tasks(cur, MAX_BATCH_TASKS)

                if not tasks:
                    logger.debug("暂无 pending 任务")
                else:
                    for task in tasks:
                        execute_task(cur, task)

        except pymysql.Error as e:
            logger.error("数据库错误: %s，%d 秒后重试", e, POLL_INTERVAL)
        except Exception:
            logger.exception("未预期异常")
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        time.sleep(POLL_INTERVAL)


def run_once(batch_uuid: Optional[str] = None) -> None:
    """单次运行：处理一个 pending 任务或指定 UUID 的任务。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if batch_uuid:
                task = fetch_task_by_uuid(cur, batch_uuid)
                if not task:
                    logger.error("未找到任务 batch_uuid=%s", batch_uuid)
                    sys.exit(1)
                execute_task(cur, task)
            else:
                tasks = fetch_pending_tasks(cur, 1)
                if not tasks:
                    logger.info("暂无 pending 任务")
                    return
                execute_task(cur, tasks[0])
    finally:
        conn.close()


# ===================================================================
# HTTP 服务模式（自带后台轮询，后端无需额外操作）
# ===================================================================

def _poll_loop(stop_event: threading.Event) -> None:
    """后台线程：持续轮询 pending 任务。"""
    logger.info("后台轮询线程启动，间隔=%ds", POLL_INTERVAL)
    while not stop_event.is_set():
        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                tasks = fetch_pending_tasks(cur, MAX_BATCH_TASKS)
                for task in tasks:
                    execute_task(cur, task)
        except pymysql.Error as e:
            logger.error("数据库错误: %s", e)
        except Exception:
            logger.exception("轮询异常")
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        stop_event.wait(POLL_INTERVAL)


def create_app() -> Flask:
    """创建 Flask 应用。"""
    app = Flask(__name__)

    @app.route("/api/rfm/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/api/rfm/process-pending", methods=["POST"])
    def process_pending():
        """立即处理所有 pending 任务。"""
        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                tasks = fetch_pending_tasks(cur, MAX_BATCH_TASKS)
                if not tasks:
                    return jsonify({"code": 200, "processed": 0})
                for task in tasks:
                    execute_task(cur, task)
                return jsonify({
                    "code": 200,
                    "processed": len(tasks),
                    "batch_uuids": [t["batch_uuid"] for t in tasks],
                })
        except Exception:
            logger.exception("process-pending 异常")
            return jsonify({"code": 500, "message": "处理失败"}), 500
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    return app


def run_server(port: int = 5000) -> None:
    """启动 HTTP 服务 + 后台轮询线程。"""
    stop_event = threading.Event()
    poller = threading.Thread(target=_poll_loop, args=(stop_event,), daemon=True)
    poller.start()

    app = create_app()
    logger.info("RFM 算法 HTTP 服务启动，端口=%d（后台轮询已就绪）", port)
    try:
        app.run(host="0.0.0.0", port=port, debug=False)
    finally:
        stop_event.set()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="算法2 - RFM 用户分群计算服务")
    parser.add_argument("--once", action="store_true", help="单次处理 pending 任务后退出")
    parser.add_argument("--batch-uuid", type=str, default=None, help="指定处理某个任务")
    parser.add_argument("--server", action="store_true", help="HTTP 服务模式（自带后台轮询）")
    parser.add_argument("--port", type=int, default=5000, help="HTTP 端口（默认 5000）")
    args = parser.parse_args()

    if args.server:
        run_server(args.port)
    elif args.once or args.batch_uuid:
        run_once(args.batch_uuid)
    else:
        run_loop()
