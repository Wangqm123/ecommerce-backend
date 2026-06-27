const mysql = require('mysql2/promise');
const fs = require('fs');
const path = require('path');

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

/**
 * 初始化数据库表结构（如果表不存在则自动创建）
 */
async function initDatabase() {
  try {
    const schemaPath = path.join(__dirname, '../sql/schema.sql');
    const schemaSQL = fs.readFileSync(schemaPath, 'utf8');
    // 分割 SQL 语句（按 ; 分割，但需避免分割字符串中的 ;）
    const statements = schemaSQL.split(';').filter(stmt => stmt.trim().length > 0);
    for (const stmt of statements) {
      await pool.execute(stmt);
    }
    console.log('✅ Database schema initialized successfully.');
  } catch (err) {
    console.error('❌ Failed to initialize database schema:', err.message);
    // 不抛出错误，让应用继续启动（可能已有表）
  }
}

module.exports = { pool, initDatabase };