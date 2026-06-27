const pool = require('../config/db');

async function getAnalysis(startDate, endDate) {
  const params = [];
  let dateFilter = '';
  if (startDate && endDate) {
    dateFilter = 'AND o.order_date BETWEEN ? AND ?';
    params.push(startDate, endDate);
  }

  const [rows] = await pool.execute(
    `SELECT
      u.province,
      SUM(o.total_amount)      AS sales_amount,
      SUM(o.quantity)          AS sales_volume,
      COUNT(DISTINCT o.order_id) AS order_count,
      COUNT(DISTINCT o.user_id)  AS user_count
    FROM orders o
    JOIN users u ON o.user_id = u.user_id
    WHERE o.order_status = 'completed' ${dateFilter}
    GROUP BY u.province
    ORDER BY sales_amount DESC`,
    params
  );

  const totalSales = rows.reduce((s, r) => s + parseFloat(r.sales_amount), 0);

  const regions = rows.map(r => ({
    province: r.province,
    salesAmount: parseFloat(r.sales_amount),
    salesVolume: r.sales_volume,
    orderCount: r.order_count,
    userCount: r.user_count,
    amountPercent: totalSales > 0 ? parseFloat(((parseFloat(r.sales_amount) / totalSales) * 100).toFixed(2)) : 0,
    avgOrderValue: r.order_count > 0 ? parseFloat((parseFloat(r.sales_amount) / r.order_count).toFixed(2)) : 0,
  }));

  return { regions, totalSales };
}

async function getProvinceDetail(province, startDate, endDate) {
  const params = [province];
  let dateFilter = '';
  if (startDate && endDate) {
    dateFilter = 'AND o.order_date BETWEEN ? AND ?';
    params.push(startDate, endDate);
  }

  const [rows] = await pool.execute(
    `SELECT
      u.city,
      SUM(o.total_amount)      AS sales_amount,
      SUM(o.quantity)          AS sales_volume,
      COUNT(DISTINCT o.order_id) AS order_count,
      COUNT(DISTINCT o.user_id)  AS user_count
    FROM orders o
    JOIN users u ON o.user_id = u.user_id
    WHERE o.order_status = 'completed' AND u.province = ? ${dateFilter}
    GROUP BY u.city
    ORDER BY sales_amount DESC`,
    params
  );

  return {
    province,
    cities: rows.map(r => ({
      city: r.city,
      salesAmount: parseFloat(r.sales_amount),
      salesVolume: r.sales_volume,
      orderCount: r.order_count,
      userCount: r.user_count,
    })),
  };
}

module.exports = { getAnalysis, getProvinceDetail };
