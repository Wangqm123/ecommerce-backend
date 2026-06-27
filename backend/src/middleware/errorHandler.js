module.exports = (err, req, res, _next) => {
  // 输出完整错误堆栈（包括 SQL 错误）
  console.error(`[${new Date().toISOString()}]`, err.stack || err);

  if (err.type === 'entity.parse.failed') {
    return res.status(400).json({ code: 400, message: '请求体JSON解析失败', data: null });
  }

  const status = err.status || 500;
  const code = err.code || status;
  const message = err.expose ? err.message : '服务器内部错误';

  res.status(status).json({ code, message, data: null });
};