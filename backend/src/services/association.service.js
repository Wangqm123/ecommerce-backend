const pool = require('../config/db');
const { v4: uuidv4 } = require('uuid');

async function trigger({ startDate, endDate, params = {} }) {
  const batchUuid = uuidv4();
  await pool.query(
    'INSERT INTO association_tasks (batch_uuid, status, params) VALUES (?, ?, ?)',
    [batchUuid, 'pending', JSON.stringify({ startDate, endDate, ...params })]
  );
  const [[task]] = await pool.query('SELECT * FROM association_tasks WHERE batch_uuid = ?', [batchUuid]);
  if (task.params) task.params = typeof task.params === 'string' ? JSON.parse(task.params) : task.params;
  return task;
}

async function getStatus(batchUuid) {
  const [rows] = await pool.query('SELECT * FROM association_tasks WHERE batch_uuid = ?', [batchUuid]);
  if (rows.length === 0) return null;
  const task = rows[0];
  if (task.params) task.params = typeof task.params === 'string' ? JSON.parse(task.params) : task.params;
  return task;
}

async function getResult({ batchUuid, sortBy = 'lift', order = 'desc', page = 1, pageSize = 20 } = {}) {
  // 如果未指定批次，取最新的 completed 批次
  if (!batchUuid) {
    const [latest] = await pool.query(
      "SELECT batch_uuid FROM association_tasks WHERE status = 'completed' ORDER BY completed_at DESC LIMIT 1"
    );
    if (latest.length === 0) {
      return { batchUuid: null, rules: [], total: 0 };
    }
    batchUuid = latest[0].batch_uuid;
    console.log('Using latest batch:', batchUuid); // 调试日志
  }

  // 查询规则数量
  const [[{ total }]] = await pool.query(
    'SELECT COUNT(*) AS total FROM association_rules WHERE compute_batch = ?',
    [batchUuid]
  );
  
  // 如果没有规则，直接返回空
  if (total === 0) {
    return { batchUuid, rules: [], total: 0 };
  }

  // ... 后续查询代码不变
}
  return {
    batchUuid,
    rules: rules.map(r => ({
      id: r.id,
      antecedent: safeJsonParse(r.antecedent),
      consequent: safeJsonParse(r.consequent),
      antecedentNames: safeJsonParse(r.antecedent_names),
      consequentNames: safeJsonParse(r.consequent_names),
      support: parseFloat(r.support),
      confidence: parseFloat(r.confidence),
      lift: parseFloat(r.lift),
      ruleType: r.rule_type,
    })),
    total: total,
    page,
    pageSize,
  };
}

async function recommend(productId, { batchUuid, topN = 10 } = {}) {
  if (!batchUuid) {
    const [latest] = await pool.query(
      "SELECT batch_uuid FROM association_tasks WHERE status = 'completed' ORDER BY completed_at DESC LIMIT 1"
    );
    if (latest.length === 0) return [];
    batchUuid = latest[0].batch_uuid;
  }

  // 查询 antecedent 包含该 product 的所有规则
  const [rules] = await pool.query(
    'SELECT * FROM association_rules WHERE compute_batch = ? ORDER BY lift DESC',
    [batchUuid]
  );

  return rules
    .filter(r => {
      const ant = safeJsonParse(r.antecedent);
      return ant && ant.includes(String(productId));
    })
    .slice(0, topN)
    .map(r => ({
      id: r.id,
      antecedent: safeJsonParse(r.antecedent),
      consequent: safeJsonParse(r.consequent),
      consequentNames: safeJsonParse(r.consequent_names),
      confidence: parseFloat(r.confidence),
      lift: parseFloat(r.lift),
    }));
}

function safeJsonParse(str) {
  if (!str) return null;
  try { return JSON.parse(str); } catch { return str; }
}

// 提供给算法同事的购物篮数据
async function getInputData(startDate, endDate) {
  const [rows] = await pool.query(
    `SELECT o.order_id, o.product_id, p.product_name, p.category
     FROM orders o JOIN products p ON o.product_id = p.product_id
     WHERE o.order_status = 'completed' AND o.order_date BETWEEN ? AND ?
     ORDER BY o.order_id`,
    [startDate, endDate]
  );

  // 按订单分组为购物篮
  const baskets = {};
  for (const r of rows) {
    if (!baskets[r.order_id]) baskets[r.order_id] = [];
    baskets[r.order_id].push({ product_id: r.product_id, product_name: r.product_name, category: r.category });
  }
  return Object.entries(baskets).map(([orderId, items]) => ({ order_id: orderId, items }));
}

module.exports = { trigger, getStatus, getResult, recommend, getInputData };
