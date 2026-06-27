const ResponseUtil = require('../utils/response');
const categoryService = require('../services/category.service');

async function getAnalysis(req, res, next) {
  try {
    const { startDate, endDate } = req.query;
    const data = await categoryService.getAnalysis(startDate, endDate);
    res.json(ResponseUtil.success(data));
  } catch (err) {
    next(err);
  }
}

async function getTrend(req, res, next) {
  try {
    const { category, startDate, endDate, granularity } = req.query;
    if (!category || !startDate || !endDate) {
      return res.status(400).json(ResponseUtil.fail(400, 'category, startDate, endDate 为必填参数'));
    }
    const data = await categoryService.getTrend(category, startDate, endDate, granularity);
    res.json(ResponseUtil.success(data));
  } catch (err) {
    next(err);
  }
}

module.exports = { getAnalysis, getTrend };
