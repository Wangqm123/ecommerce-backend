const ResponseUtil = require('../utils/response');
const uploadService = require('../services/upload.service');
const fs = require('fs');

async function uploadCSV(req, res, next) {
  try {
    if (!req.file) {
      return res.status(400).json(ResponseUtil.fail(2001, '请上传 CSV 文件'));
    }
    const result = await uploadService.importCSV(req.file.path, req.file.originalname, req.file.size);
    res.json(ResponseUtil.success(result, '导入完成'));
  } catch (err) {
    next(err);
  }
}

async function getHistory(req, res, next) {
  try {
    const page = parseInt(req.query.page) || 1;
    const pageSize = Math.min(parseInt(req.query.pageSize) || 20, 100);
    const result = await uploadService.getHistory(page, pageSize);
    res.json(ResponseUtil.paginate(result.rows, result.total, page, pageSize));
  } catch (err) {
    next(err);
  }
}

async function getBatchDetail(req, res, next) {
  try {
    const detail = await uploadService.getBatchDetail(req.params.batchId);
    if (!detail) return res.status(404).json(ResponseUtil.fail(404, '批次不存在'));
    res.json(ResponseUtil.success(detail));
  } catch (err) {
    next(err);
  }
}

module.exports = { uploadCSV, getHistory, getBatchDetail };
