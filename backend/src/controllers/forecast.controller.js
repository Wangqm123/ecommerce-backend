const ResponseUtil = require('../utils/response');
const forecastService = require('../services/forecast.service');

async function trigger(req, res, next) {
  try {
    const task = await forecastService.trigger(req.body);
    res.json(ResponseUtil.success({
      batchUuid: task.batch_uuid,
      taskId: task.id,
      status: task.status,
      message: '预测任务已创建，请等待算法侧执行后查询结果',
    }));
  } catch (err) {
    next(err);
  }
}

async function getStatus(req, res, next) {
  try {
    const task = await forecastService.getStatus(req.params.batchUuid);
    if (!task) return res.status(404).json(ResponseUtil.fail(404, '任务不存在'));
    res.json(ResponseUtil.success(task));
  } catch (err) {
    next(err);
  }
}

async function getResult(req, res, next) {
  try {
    const data = await forecastService.getResult(req.query);
    res.json(ResponseUtil.success(data));
  } catch (err) {
    next(err);
  }
}

module.exports = { trigger, getStatus, getResult };
