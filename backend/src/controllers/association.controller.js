const ResponseUtil = require('../utils/response');
const associationService = require('../services/association.service');

async function trigger(req, res, next) {
  try {
    const task = await associationService.trigger(req.body);
    res.json(ResponseUtil.success({
      batchUuid: task.batch_uuid,
      taskId: task.id,
      status: task.status,
      message: '关联规则计算任务已创建，请等待算法侧执行后查询结果',
    }));
  } catch (err) {
    next(err);
  }
}

async function getStatus(req, res, next) {
  try {
    const task = await associationService.getStatus(req.params.batchUuid);
    if (!task) return res.status(404).json(ResponseUtil.fail(404, '任务不存在'));
    res.json(ResponseUtil.success(task));
  } catch (err) {
    next(err);
  }
}

async function getResult(req, res, next) {
  try {
    const data = await associationService.getResult(req.query);
    res.json(ResponseUtil.success(data));
  } catch (err) {
    next(err);
  }
}

async function recommend(req, res, next) {
  try {
    const { topN } = req.query;
    const data = await associationService.recommend(req.params.productId, { topN: parseInt(topN) || 10, batchUuid: req.query.batchUuid });
    res.json(ResponseUtil.success(data));
  } catch (err) {
    next(err);
  }
}

module.exports = { trigger, getStatus, getResult, recommend };
