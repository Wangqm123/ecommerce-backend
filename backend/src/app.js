const express = require('express');
const cors = require('cors');
const morgan = require('morgan');
const errorHandler = require('./middleware/errorHandler');
const routes = require('./routes');

const app = express();

// ========== 强制 CORS 中间件（放在最前面） ==========
app.use((req, res, next) => {
  // 允许所有来源（可后续改为具体域名）
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Access-Control-Allow-Credentials', 'true');

  // 处理预检请求（OPTIONS）
  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }
  next();
});

// ========== 原有的 CORS 配置（保留但可能被覆盖） ==========
const corsOptions = {
  origin: process.env.CORS_ORIGIN
    ? process.env.CORS_ORIGIN.split(',').map(o => o.trim())
    : '*',
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
};
app.use(cors(corsOptions));

// 日志
app.use(morgan('dev'));

// 解析 JSON 和 URL 编码
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// 路由
app.use('/api', routes);

// 健康检查
app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

// 全局错误处理
app.use(errorHandler);

module.exports = app;