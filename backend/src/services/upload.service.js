const pool = require('../config/db');
const { parseCSV } = require('../utils/csvParser');
const { validateRows } = require('../utils/validator');
const fs = require('fs');

const BATCH_SIZE = 500;

async function importCSV(filePath, fileName, fileSize) {
  // 创建导入批次记录
  const [batchResult] = await pool.execute(
    'INSERT INTO import_batches (file_name, file_size, total_rows, status) VALUES (?, ?, 0, ?)',
    [fileName, fileSize, 'processing']
  );
  const batchId = batchResult.insertId;

  try {
    // 解析 CSV
    const rows = await parseCSV(filePath);
    await pool.execute('UPDATE import_batches SET total_rows = ? WHERE id = ?', [rows.length, batchId]);

    // 校验
    const { validRows, errors } = validateRows(rows);

    // 分批插入
    for (let i = 0; i < validRows.length; i += BATCH_SIZE) {
      const batch = validRows.slice(i, i + BATCH_SIZE);
      await insertBatch(batch);
    }

    // 更新订单汇总
    await refreshOrderSummary();

    // 更新批次状态
    await pool.execute(
      'UPDATE import_batches SET status = ?, success_rows = ?, failed_rows = ?, error_log = ? WHERE id = ?',
      ['completed', validRows.length, errors.length, JSON.stringify(errors), batchId]
    );

    return {
      batchId,
      fileName,
      totalRows: rows.length,
      successRows: validRows.length,
      failedRows: errors.length,
      status: 'completed',
      errors,
    };
  } catch (err) {
    await pool.execute(
      'UPDATE import_batches SET status = ?, failed_rows = ?, error_log = ? WHERE id = ?',
      ['failed', 0, JSON.stringify([{ row: 0, reason: err.message }]), batchId]
    );
    throw err;
  } finally {
    // 删除临时文件
    fs.unlink(filePath, () => {});
  }
}

async function insertBatch(rows) {
  const conn = await pool.getConnection();
  try {
    await conn.beginTransaction();

    // 去重插入 products
    const productValues = [];
    const productIds = new Set();
    for (const r of rows) {
      if (productIds.has(r.product_id)) continue;
      productIds.add(r.product_id);
      productValues.push([r.product_id, r.product_name, r.category, parseFloat(r.unit_price)]);
    }
    if (productValues.length > 0) {
      await conn.query(
        `INSERT INTO products (product_id, product_name, category, unit_price) VALUES ? ON DUPLICATE KEY UPDATE product_name=VALUES(product_name), category=VALUES(category), unit_price=VALUES(unit_price)`,
        [productValues]
      );
    }

    // 去重插入 users
    const userValues = [];
    const userIds = new Set();
    for (const r of rows) {
      if (userIds.has(r.user_id)) continue;
      userIds.add(r.user_id);
      userValues.push([r.user_id, r.province, r.city || '']);
    }
    if (userValues.length > 0) {
      await conn.query(
        `INSERT INTO users (user_id, province, city) VALUES ? ON DUPLICATE KEY UPDATE province=VALUES(province), city=VALUES(city)`,
        [userValues]
      );
    }

    // 插入 orders
    const orderValues = rows.map(r => [
      r.order_id, parseInt(r.product_id), parseInt(r.user_id),
      parseInt(r.quantity), parseFloat(r.unit_price), parseFloat(r.total_amount),
      r.order_date, r.order_status || 'completed',
    ]);
    await conn.query(
      `INSERT INTO orders (order_id, product_id, user_id, quantity, unit_price, total_amount, order_date, order_status) VALUES ? ON DUPLICATE KEY UPDATE quantity=VALUES(quantity), total_amount=VALUES(total_amount)`,
      [orderValues]
    );

    await conn.commit();
  } catch (err) {
    await conn.rollback();
    throw err;
  } finally {
    conn.release();
  }
}

async function refreshOrderSummary() {
  await pool.execute(`
    INSERT INTO order_summary (order_id, user_id, total_amount, item_count, order_date)
    SELECT o.order_id, MIN(o.user_id), SUM(o.total_amount), COUNT(DISTINCT o.product_id), MIN(o.order_date)
    FROM orders o
    LEFT JOIN order_summary os ON o.order_id = os.order_id
    WHERE os.order_id IS NULL
    GROUP BY o.order_id
    ON DUPLICATE KEY UPDATE total_amount=VALUES(total_amount), item_count=VALUES(item_count)
  `);
}

async function getHistory(page = 1, pageSize = 20) {
  const offset = (page - 1) * pageSize;
  const [[{ total }]] = await pool.execute('SELECT COUNT(*) AS total FROM import_batches');
  const [rows] = await pool.execute(
    `SELECT * FROM import_batches ORDER BY imported_at DESC LIMIT ${offset}, ${pageSize}`,
    []
  );
  return { rows, total: total, page, pageSize };
}

async function getBatchDetail(batchId) {
  const [rows] = await pool.execute('SELECT * FROM import_batches WHERE id = ?', [batchId]);
  return rows[0] || null;
}

module.exports = { importCSV, getHistory, getBatchDetail };
