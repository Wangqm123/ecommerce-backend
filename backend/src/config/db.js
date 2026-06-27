const mysql = require('mysql2/promise');

let poolConfig = {};

// 优先使用 Railway 提供的 MYSQL_URL 或 DATABASE_URL
const dbUrl = process.env.MYSQL_URL || process.env.DATABASE_URL;

if (dbUrl) {
  poolConfig = {
    uri: dbUrl,
    connectionLimit: parseInt(process.env.DB_CONNECTION_LIMIT) || 10,
    charset: 'utf8mb4',
    timezone: '+08:00',
    dateStrings: true,
    waitForConnections: true,
    queueLimit: 0,
  };
} else {
  // 本地开发使用独立变量
  poolConfig = {
    host: process.env.DB_HOST || '127.0.0.1',
    port: parseInt(process.env.DB_PORT) || 3306,
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || '',
    database: process.env.DB_NAME || 'ecommerce_analysis',
    connectionLimit: parseInt(process.env.DB_CONNECTION_LIMIT) || 10,
    charset: 'utf8mb4',
    timezone: '+08:00',
    dateStrings: true,
    waitForConnections: true,
    queueLimit: 0,
  };
}

const pool = mysql.createPool(poolConfig);
module.exports = pool;