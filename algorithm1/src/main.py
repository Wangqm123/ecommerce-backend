import json
import time
import sys
import traceback
from pathlib import Path

# 添加项目根目录到路径（确保 config 可导入）
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import MODE
from src.logger import setup_logger

logger = setup_logger()

# 根据 MODE 导入不同的实现
if MODE == 'mock':
    logger.info("Running in MOCK mode (using simulated data, no database required)")
    from src.mock_impl import MockTaskFetcher, MockTrainingDataProvider, MockResultWriter

    task_fetcher = MockTaskFetcher()
    data_provider = MockTrainingDataProvider()
    result_writer = MockResultWriter()
    # mock 模式下不需要数据库引擎
    engine = None
else:
    logger.info("Running in REAL mode (using MySQL database)")
    from src.db_utils import get_engine, fetch_pending_task, update_task_status, get_training_data, \
        write_forecast_results

    engine = get_engine()


    # 将函数封装为对象，保持接口统一
    class RealTaskFetcher:
        def fetch_pending_task(self):
            return fetch_pending_task(engine)

        def update_task_status(self, batch_uuid, status, error_msg=None):
            update_task_status(engine, batch_uuid, status, error_msg)


    class RealDataProvider:
        def get_training_data(self, start_date, end_date, product_ids=None):
            return get_training_data(engine, start_date, end_date, product_ids)


    class RealResultWriter:
        def write_forecast_results(self, batch_uuid, product_id, product_name, forecasts_df, model_name):
            write_forecast_results(engine, batch_uuid, product_id, product_name, forecasts_df, model_name)


    task_fetcher = RealTaskFetcher()
    data_provider = RealDataProvider()
    result_writer = RealResultWriter()

# 导入预测模型
from src.forecast_model import forecast_for_product


def process_task(task):
    batch_uuid = task['batch_uuid']
    params = json.loads(task['params'])

    start_date = params.get('startDate')
    end_date = params.get('endDate')
    forecast_days = params.get('forecastDays', 30)
    target_product_ids = params.get('targetProductIds', [])  # 可能为 None 或空列表
    model_name = params.get('model', 'prophet')

    logger.info(
        f"Processing task {batch_uuid}: {start_date} to {end_date}, forecast {forecast_days} days, model={model_name}")

    # 1. 获取训练数据
    df_raw = data_provider.get_training_data(start_date, end_date, target_product_ids if target_product_ids else None)
    if df_raw.empty:
        raise Exception(f"No training data found for period {start_date} - {end_date}")

    # 2. 按商品分组预测
    grouped = df_raw.groupby(['product_id', 'product_name'])
    product_count = len(grouped)
    logger.info(f"Found {product_count} products to forecast")

    for idx, ((prod_id, prod_name), group) in enumerate(grouped, 1):
        logger.info(f"[{idx}/{product_count}] Forecasting for product {prod_id} - {prod_name}")
        ts = group[['order_date', 'daily_quantity']].copy()
        forecasts = forecast_for_product(ts, forecast_days, model_name)
        result_writer.write_forecast_results(batch_uuid, prod_id, prod_name, forecasts, model_name)

    logger.info(f"Task {batch_uuid} completed, wrote forecasts for {product_count} products")


def main_loop():
    logger.info("Forecast service started. Polling every 10 seconds...")
    while True:
        try:
            task = task_fetcher.fetch_pending_task()
            if task is None:
                time.sleep(10)
                continue

            batch_uuid = task['batch_uuid']
            # 更新状态为 running
            task_fetcher.update_task_status(batch_uuid, 'running')

            # 处理任务
            process_task(task)

            # 更新状态为 completed
            task_fetcher.update_task_status(batch_uuid, 'completed')

        except Exception as e:
            logger.error(f"Task failed: {e}")
            traceback.print_exc()
            if 'batch_uuid' in locals():
                task_fetcher.update_task_status(batch_uuid, 'failed', error_msg=str(e))
            time.sleep(10)

        time.sleep(10)


if __name__ == '__main__':
    main_loop()