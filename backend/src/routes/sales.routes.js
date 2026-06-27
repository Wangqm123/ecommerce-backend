const router = require('express').Router();
const ctrl = require('../controllers/sales.controller');

router.get('/ranking', ctrl.getRanking);

module.exports = router;
