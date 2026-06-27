const pool = require('../config/db');

async function getRanking({ rankBy = 'salesAmount', order = 'desc', limit = 20, category, startDate, endDate } = {}) {
  const orderField = rankBy === 'salesVolume' ? 'sales_volume' : 'sales_amount';
  const orderDir = order === 'asc' ? 'ASC' : 'DESC';
  const params = [];
  let categoryFilter = '';
  let dateFilter = '';

  if (category) {
    categoryFilter = 'AND p.category = ?';
    params.push(category);
  }
  if (startDate && endDate) {
    dateFilter = 'AND o.order_date BETWEEN ? AND ?';
    params.push(startDate, endDate);
  }

  const safeLimit = Math.min(parseInt(limit) || 20, 100);

  // 时间段内总销售额（用于占比计算）
  let totalSales = 0;
  if (startDate && endDate) {
    const [[t]] = await pool.query(
      'SELECT SUM(total_amount) AS total FROM orders WHERE order_status = ? AND order_date BETWEEN ? AND ?',
      ['completed', startDate, endDate]
    );
    totalSales = parseFloat(t.total) || 0;
  }

  const [rows] = await pool.query(
    `SELECT
      o.product_id,
      p.product_name,
      p.category,
      p.unit_price,
      SUM(o.quantity)     AS sales_volume,
      SUM(o.total_amount) AS sales_amount
    FROM orders o
    JOIN products p ON o.product_id = p.product_id
    WHERE o.order_status = 'completed' ${categoryFilter} ${dateFilter}
    GROUP BY o.product_id, p.product_name, p.category, p.unit_price
    ORDER BY ${orderField} ${orderDir}
    LIMIT ${safeLimit}`,
    [...params]
  );

  // 如果没有日期范围，用全量总额
  if (!totalSales || totalSales === 0) {
    const [[t]] = await pool.query(
      "SELECT SUM(total_amount) AS total FROM orders WHERE order_status = 'completed'"
    );
    totalSales = parseFloat(t.total) || 0;
  }

  const rankings = rows.map((r, i) => ({
    rank: i + 1,
    productId: r.product_id,
    productName: r.product_name,
    category: r.category,
    unitPrice: parseFloat(r.unit_price),
    salesVolume: r.sales_volume,
    salesAmount: parseFloat(r.sales_amount),
    sharePercent: totalSales > 0 ? parseFloat(((parseFloat(r.sales_amount) / totalSales) * 100).toFixed(2)) : 0,
  }));

  const [[{ total }]] = await pool.query(
    `SELECT COUNT(DISTINCT o.product_id) AS total FROM orders o JOIN products p ON o.product_id = p.product_id WHERE o.order_status = 'completed' ${categoryFilter} ${dateFilter}`,
    params
  );

  return { rankings, total: total };
}

module.exports = { getRanking };
