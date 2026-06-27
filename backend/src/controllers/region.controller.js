const ResponseUtil = require('../utils/response');
const regionService = require('../services/region.service');

async function getAnalysis(req, res, next) {
  try {
    const { startDate, endDate } = req.query;
    const data = await regionService.getAnalysis(startDate, endDate);
    res.json(ResponseUtil.success(data));
  } catch (err) {
    next(err);
  }
}

async function getProvinceDetail(req, res, next) {
  try {
    const { province } = req.params;
    const { startDate, endDate } = req.query;
    const data = await regionService.getProvinceDetail(decodeURIComponent(province), startDate, endDate);
    res.json(ResponseUtil.success(data));
  } catch (err) {
    next(err);
  }
}

module.exports = { getAnalysis, getProvinceDetail };
