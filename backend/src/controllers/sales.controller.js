const ResponseUtil = require('../utils/response');
const salesService = require('../services/sales.service');

async function getRanking(req, res, next) {
  try {
    const data = await salesService.getRanking(req.query);
    res.json(ResponseUtil.success(data));
  } catch (err) {
    next(err);
  }
}

module.exports = { getRanking };
