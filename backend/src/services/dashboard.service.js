const pool = require('../config/db');

async function getKPIs(startDate, endDate) {
  const params = [];
  let dateFilter = '';
  if (startDate && endDate) {
    dateFilter = 'AND order_date BETWEEN ? AND ?';
    params.push(startDate, endDate);
  }

  const [rows] = await pool.query(
    `SELECT
      COUNT(DISTINCT order_id) AS totalOrders,
      COUNT(DISTINCT user_id)  AS totalUsers,
      SUM(total_amount)        AS totalSales,
      SUM(quantity)            AS totalQuantity,
      ROUND(SUM(total_amount) / NULLIF(COUNT(DISTINCT order_id), 0), 2) AS avgOrderValue
    FROM orders WHERE order_status = 'completed' ${dateFilter}`,
    params
  );

  const [[{ totalProducts }]] = await pool.query('SELECT COUNT(*) AS totalProducts FROM products');

  // 环比计算：与前一个等长周期比较
  let compare = { salesGrowth: 0, orderGrowth: 0, userGrowth: 0 };
  if (startDate && endDate) {
    const days = Math.ceil((new Date(endDate) - new Date(startDate)) / (1000 * 60 * 60 * 24));
    const prevEnd = new Date(startDate);
    prevEnd.setDate(prevEnd.getDate() - 1);
    const prevStart = new Date(prevEnd);
    prevStart.setDate(prevStart.getDate() - days);
    const prevEndStr = prevEnd.toISOString().split('T')[0];
    const prevStartStr = prevStart.toISOString().split('T')[0];

    const [prev] = await pool.query(
      `SELECT
        COUNT(DISTINCT order_id) AS totalOrders,
        COUNT(DISTINCT user_id)  AS totalUsers,
        SUM(total_amount)        AS totalSales
      FROM orders WHERE order_status = 'completed' AND order_date BETWEEN ? AND ?`,
      [prevStartStr, prevEndStr]
    );

    if (prev[0] && prev[0].totalSales > 0) {
      compare.salesGrowth = parseFloat((((rows[0].totalSales - prev[0].totalSales) / prev[0].totalSales) * 100).toFixed(1));
      compare.orderGrowth = parseFloat((((rows[0].totalOrders - prev[0].totalOrders) / prev[0].totalOrders) * 100).toFixed(1));
      compare.userGrowth = parseFloat((((rows[0].totalUsers - prev[0].totalUsers) / prev[0].totalUsers) * 100).toFixed(1));
    }
  }

  return {
    totalSales: parseFloat(rows[0].totalSales) || 0,
    totalOrders: rows[0].totalOrders || 0,
    totalUsers: rows[0].totalUsers || 0,
    totalProducts: totalProducts || 0,
    totalQuantity: rows[0].totalQuantity || 0,
    avgOrderValue: parseFloat(rows[0].avgOrderValue) || 0,
    compareLastPeriod: compare,
  };
}

async function getTrend(startDate, endDate, granularity = 'day') {
  let format;
  switch (granularity) {
    case 'week': format = '%Y-%u'; break;
    case 'month': format = '%Y-%m'; break;
    default: format = '%Y-%m-%d'; break;
  }

  const [rows] = await pool.query(
    `SELECT
      DATE_FORMAT(order_date, ?) AS period,
      SUM(total_amount) AS sales,
      COUNT(DISTINCT order_id) AS orders,
      COUNT(DISTINCT user_id) AS users,
      SUM(quantity) AS quantity
    FROM orders WHERE order_status = 'completed' AND order_date BETWEEN ? AND ?
    GROUP BY period ORDER BY period`,
    [format, startDate, endDate]
  );

  return rows.map(r => ({
    period: r.period,
    sales: parseFloat(r.sales),
    orders: r.orders,
    users: r.users,
    quantity: r.quantity,
  }));
}

module.exports = { getKPIs, getTrend };
