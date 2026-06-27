const ResponseUtil = require('../utils/response');
const dashboardService = require('../services/dashboard.service');

async function getKPIs(req, res, next) {
  try {
    const { startDate, endDate } = req.query;
    const data = await dashboardService.getKPIs(startDate, endDate);
    res.json(ResponseUtil.success(data));
  } catch (err) {
    next(err);
  }
}

async function getTrend(req, res, next) {
  try {
    const { startDate, endDate, granularity } = req.query;
    if (!startDate || !endDate) {
      return res.status(400).json(ResponseUtil.fail(400, 'startDate 和 endDate 为必填参数'));
    }
    const data = await dashboardService.getTrend(startDate, endDate, granularity);
    res.json(ResponseUtil.success(data));
  } catch (err) {
    next(err);
  }
}

module.exports = { getKPIs, getTrend };
