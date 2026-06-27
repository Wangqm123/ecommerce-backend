const pool = require('../config/db');
const { v4: uuidv4 } = require('uuid');

async function trigger({ startDate, endDate, recencyBaseDate, params = {} }) {
  const batchUuid = uuidv4();
  await pool.query(
    'INSERT INTO rfm_compute_tasks (batch_uuid, status, params) VALUES (?, ?, ?)',
    [batchUuid, 'pending', JSON.stringify({ startDate, endDate, recencyBaseDate, ...params })]
  );
  const [[task]] = await pool.query('SELECT * FROM rfm_compute_tasks WHERE batch_uuid = ?', [batchUuid]);
  return task;
}

async function getStatus(batchUuid) {
  const [rows] = await pool.query('SELECT * FROM rfm_compute_tasks WHERE batch_uuid = ?', [batchUuid]);
  if (rows.length === 0) return null;
  const task = rows[0];
  if (task.params) task.params = typeof task.params === 'string' ? JSON.parse(task.params) : task.params;
  return task;
}

async function getResult({ batchUuid, segment, page = 1, pageSize = 20 } = {}) {
  // 如果不指定批次，取最新的 completed 批次
  if (!batchUuid) {
    const [latest] = await pool.query(
      "SELECT batch_uuid FROM rfm_compute_tasks WHERE status = 'completed' ORDER BY completed_at DESC LIMIT 1"
    );
    if (latest.length === 0) return { batchUuid: null, segments: [], users: [], userCount: 0 };
    batchUuid = latest[0].batch_uuid;
  }

  const params = [batchUuid];
  let segmentFilter = '';
  if (segment) {
    segmentFilter = 'AND rfm_segment = ?';
    params.push(segment);
  }

  // 分层统计
  const [segRows] = await pool.query(
    `SELECT rfm_segment, COUNT(*) AS user_count, ROUND(AVG(monetary), 2) AS avg_monetary
     FROM rfm_results WHERE compute_batch = ? GROUP BY rfm_segment ORDER BY avg_monetary DESC`,
    [batchUuid]
  );
  const totalUsers = segRows.reduce((s, r) => s + r.user_count, 0);
  const segments = segRows.map(r => ({
    segment: r.rfm_segment,
    userCount: r.user_count,
    avgMonetary: parseFloat(r.avg_monetary),
    percent: totalUsers > 0 ? parseFloat(((r.user_count / totalUsers) * 100).toFixed(2)) : 0,
  }));

  // 用户列表
  const offset = (page - 1) * pageSize;
  const [[{ total }]] = await pool.query(
    `SELECT COUNT(*) AS total FROM rfm_results WHERE compute_batch = ? ${segmentFilter}`,
    params
  );
  const [users] = await pool.query(
    `SELECT user_id, recency, frequency, monetary, r_score, f_score, m_score, rfm_segment, rfm_group
     FROM rfm_results WHERE compute_batch = ? ${segmentFilter} ORDER BY monetary DESC LIMIT ${offset}, ${pageSize}`,
    [...params]
  );

  return { batchUuid, userCount: totalUsers, segments, users: users.map(u => ({ ...u, monetary: parseFloat(u.monetary) })), total: total, page, pageSize };
}

async function getUserDetail(userId, batchUuid) {
  if (!batchUuid) {
    const [latest] = await pool.query(
      "SELECT batch_uuid FROM rfm_compute_tasks WHERE status = 'completed' ORDER BY completed_at DESC LIMIT 1"
    );
    if (latest.length === 0) return null;
    batchUuid = latest[0].batch_uuid;
  }
  const [rows] = await pool.query(
    'SELECT * FROM rfm_results WHERE user_id = ? AND compute_batch = ?', [userId, batchUuid]
  );
  if (rows.length === 0) return null;
  const r = rows[0];
  return { ...r, monetary: parseFloat(r.monetary) };
}

// 提供给算法同事的数据查询
async function getInputData(startDate, endDate, recencyBaseDate) {
  const base = recencyBaseDate || new Date().toISOString().split('T')[0];
  const [rows] = await pool.query(
    `SELECT
      user_id,
      DATEDIFF(?, MAX(order_date)) AS recency,
      COUNT(DISTINCT order_id)      AS frequency,
      SUM(total_amount)             AS monetary
    FROM orders WHERE order_status = 'completed' AND order_date BETWEEN ? AND ?
    GROUP BY user_id`,
    [base, startDate, endDate]
  );
  return rows.map(r => ({ ...r, monetary: parseFloat(r.monetary) }));
}

module.exports = { trigger, getStatus, getResult, getUserDetail, getInputData };
