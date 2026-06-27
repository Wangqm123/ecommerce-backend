const pool = require('../config/db');
const { v4: uuidv4 } = require('uuid');

async function trigger({ startDate, endDate, forecastDays = 30, targetProductIds = [], params = {} }) {
  const batchUuid = uuidv4();
  await pool.query(
    'INSERT INTO forecast_tasks (batch_uuid, status, params) VALUES (?, ?, ?)',
    [batchUuid, 'pending', JSON.stringify({ startDate, endDate, forecastDays, targetProductIds, ...params })]
  );
  const [[task]] = await pool.query('SELECT * FROM forecast_tasks WHERE batch_uuid = ?', [batchUuid]);
  if (task.params) task.params = typeof task.params === 'string' ? JSON.parse(task.params) : task.params;
  return task;
}

async function getStatus(batchUuid) {
  const [rows] = await pool.query('SELECT * FROM forecast_tasks WHERE batch_uuid = ?', [batchUuid]);
  if (rows.length === 0) return null;
  const task = rows[0];
  if (task.params) task.params = typeof task.params === 'string' ? JSON.parse(task.params) : task.params;
  return task;
}

async function getResult({ batchUuid, productId, page = 1, pageSize = 100 } = {}) {
  if (!batchUuid) {
    const [latest] = await pool.query(
      "SELECT batch_uuid FROM forecast_tasks WHERE status = 'completed' ORDER BY completed_at DESC LIMIT 1"
    );
    if (latest.length === 0) return { batchUuid: null, forecasts: [] };
    batchUuid = latest[0].batch_uuid;
  }

  // 按产品分组返回
  let productFilter = '';
  const params = [batchUuid];
  if (productId) {
    productFilter = 'AND product_id = ?';
    params.push(productId);
  }

  const offset = (page - 1) * pageSize;
  const [[{ total }]] = await pool.query(
    `SELECT COUNT(*) AS total FROM forecast_results WHERE compute_batch = ? ${productFilter}`, params
  );
  const [rows] = await pool.query(
    `SELECT * FROM forecast_results WHERE compute_batch = ? ${productFilter} ORDER BY product_id, forecast_date LIMIT ${offset}, ${pageSize}`,
    [...params]
  );

  // 按 product_id 分组
  const productMap = {};
  for (const r of rows) {
    if (!productMap[r.product_id]) {
      productMap[r.product_id] = {
        productId: r.product_id,
        productName: r.product_name,
        modelName: r.model_name,
        forecasts: [],
      };
    }
    productMap[r.product_id].forecasts.push({
      date: r.forecast_date,
      predictedQty: r.predicted_qty,
      lowerBound: r.lower_bound,
      upperBound: r.upper_bound,
    });
  }

  return {
    batchUuid,
    products: Object.values(productMap),
    total,
    page,
    pageSize,
  };
}

// 提供给算法同事的输入数据
async function getInputData(startDate, endDate, targetProductIds = []) {
  let productFilter = '';
  const params = [startDate, endDate];
  if (targetProductIds && targetProductIds.length > 0) {
    productFilter = `AND o.product_id IN (${targetProductIds.map(() => '?').join(',')})`;
    params.push(...targetProductIds);
  }

  const [rows] = await pool.query(
    `SELECT o.product_id, p.product_name, o.order_date, SUM(o.quantity) AS daily_quantity, SUM(o.total_amount) AS daily_sales
     FROM orders o JOIN products p ON o.product_id = p.product_id
     WHERE o.order_status = 'completed' AND o.order_date BETWEEN ? AND ? ${productFilter}
     GROUP BY o.product_id, p.product_name, o.order_date ORDER BY o.product_id, o.order_date`,
    params
  );
  return rows.map(r => ({ ...r, daily_sales: parseFloat(r.daily_sales) }));
}

module.exports = { trigger, getStatus, getResult, getInputData };
