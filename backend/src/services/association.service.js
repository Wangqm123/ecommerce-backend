const pool = require('../config/db');
const { v4: uuidv4 } = require('uuid');

async function trigger({ startDate, endDate, params = {} }) {
  const batchUuid = uuidv4();
  await pool.query(
    'INSERT INTO association_tasks (batch_uuid, status, params) VALUES (?, ?, ?)',
    [batchUuid, 'pending', JSON.stringify({ startDate, endDate, ...params })]
  );
  const [rows] = await pool.query('SELECT * FROM association_tasks WHERE batch_uuid = ?', [batchUuid]);
  return rows[0];
}

async function getStatus(batchUuid) {
  const [rows] = await pool.query('SELECT * FROM association_tasks WHERE batch_uuid = ?', [batchUuid]);
  if (rows.length === 0) return null;
  const task = rows[0];
  if (task.params) task.params = typeof task.params === 'string' ? JSON.parse(task.params) : task.params;
  return task;
}
async function getResult({ batchUuid, sortBy = 'lift', order = 'desc', page = 1, pageSize = 20 } = {}) {
  // 如果未指定批次，从 association_rules 表取最新的 compute_batch
  if (!batchUuid) {
    const [latest] = await pool.query(
      "SELECT compute_batch FROM association_rules ORDER BY created_at DESC LIMIT 1"
    );
    if (latest.length === 0) {
      return { batchUuid: null, rules: [], total: 0 };
    }
    batchUuid = latest[0].compute_batch;
  }

  const [[{ total }]] = await pool.query(
    'SELECT COUNT(*) AS total FROM association_rules WHERE compute_batch = ?',
    [batchUuid]
  );
  if (total === 0) {
    return { batchUuid, rules: [], total: 0 };
  }

  const sortField = ['support', 'confidence', 'lift'].includes(sortBy) ? sortBy : 'lift';
  const sortDir = order === 'asc' ? 'ASC' : 'DESC';
  const offset = (page - 1) * pageSize;

  const [rules] = await pool.query(
    `SELECT * FROM association_rules WHERE compute_batch = ? ORDER BY ${sortField} ${sortDir} LIMIT ? OFFSET ?`,
    [batchUuid, pageSize, offset]
  );

  return {
    batchUuid,
    rules: rules.map(r => ({
      id: r.id,
      antecedent: JSON.parse(r.antecedent),
      consequent: JSON.parse(r.consequent),
      antecedentNames: JSON.parse(r.antecedent_names),
      consequentNames: JSON.parse(r.consequent_names),
      support: parseFloat(r.support),
      confidence: parseFloat(r.confidence),
      lift: parseFloat(r.lift),
      ruleType: r.rule_type,
    })),
    total,
    page,
    pageSize,
  };
}

async function recommend(productId, { batchUuid, topN = 10 } = {}) {
  if (!batchUuid) {
    // 原版本：若未指定批次，则返回空数组（不自动查找最新批次）
    return [];
  }

  const [rules] = await pool.query(
    'SELECT * FROM association_rules WHERE compute_batch = ? ORDER BY lift DESC',
    [batchUuid]
  );

  return rules
    .filter(r => {
      const ant = JSON.parse(r.antecedent);
      return ant && ant.includes(String(productId));
    })
    .slice(0, topN)
    .map(r => ({
      id: r.id,
      antecedent: JSON.parse(r.antecedent),
      consequent: JSON.parse(r.consequent),
      consequentNames: JSON.parse(r.consequent_names),
      confidence: parseFloat(r.confidence),
      lift: parseFloat(r.lift),
    }));
}

module.exports = { trigger, getStatus, getResult, recommend };