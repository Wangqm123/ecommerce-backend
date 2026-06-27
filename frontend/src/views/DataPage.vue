<template>
  <div class="wrap">
    <h1>电商销售数据分析网站</h1>
    <!-- 时间筛选 -->
    <div class="date-filter">
      <label>开始日期：</label>
      <input type="date" v-model="dateRange.startDate" />
      <label>结束日期：</label>
      <input type="date" v-model="dateRange.endDate" />
      <button class="blue-btn" @click="fetchAllData">刷新数据</button>
    </div>
    <!-- CSV导入模块 -->
    <div class="module">
      <div class="module-header">
        <span>CSV 数据导入</span>
      </div>
      <div class="module-body" v-show="show.csv">
        <input type="file" accept=".csv" @change="selectFile" />
        <button class="blue-btn" @click="uploadCSV">上传导入</button>
        <div v-if="uploadResult" class="upload-result">
          {{ uploadResult.message }}
          <div v-if="uploadResult.data.errors.length">
            <p>失败行：</p>
            <ul>
              <li v-for="err in uploadResult.data.errors" :key="err.row">
                第{{ err.row }}行：{{ err.reason }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
    <!-- 核心指标卡片 -->
    <div class="card-group">
      <div class="card">
        <h3>总订单</h3>
        <div class="num">{{ data.totalOrders }}</div>
      </div>
      <div class="card">
        <h3>总销售额</h3>
        <div class="num">¥{{ data.totalSales }}</div>
      </div>
      <div class="card">
        <h3>总用户</h3>
        <div class="num">{{ data.totalUsers }}</div>
      </div>
      <div class="card">
        <h3>平均客单价</h3>
        <div class="num">¥{{ data.avgOrderValue }}</div>
      </div>
    </div>
    <!-- 商品销售排行（横向柱状图） -->
    <div class="module">
      <div class="module-header">
        <div class="title-row">
          <span>商品销售排行</span>
          <select v-model="rankType" @change="handleRankChange">
            <option value="salesVolume">销量</option>
            <option value="salesAmount">销售额</option>
          </select>
        </div>
        <button class="blue-btn" @click="show.rank = !show.rank">
          {{ show.rank ? '收起' : '展开' }}
        </button>
      </div>
      <div class="module-body" v-show="show.rank">
        <div class="rank-chart-container">
          <div id="rankChart" class="chart-item"></div>
        </div>
      </div>
    </div>
    <!-- 商品分类销售分析 -->
    <div class="module">
      <div class="module-header">
        <div class="title-row">
          <span>商品分类销售分析</span>
        </div>
        <button class="blue-btn" @click="show.cate = !show.cate">
          {{ show.cate ? '收起' : '展开' }}
        </button>
      </div>
      <div class="module-body" v-show="show.cate">
        <div id="cateChart" class="chart-item"></div>
      </div>
    </div>
    <!-- 省份地域销售分析 -->
    <div class="module">
      <div class="module-header">
        <div class="title-row">
          <span>省份地域销售分析</span>
          <select v-model="selectedArea" @change="handleAreaChange">
            <option value="全国">全国</option>
            <option v-for="item in provinceList" :key="item" :value="item">{{ item }}</option>
          </select>
        </div>
        <button class="blue-btn" @click="show.area = !show.area">
          {{ show.area ? '收起' : '展开' }}
        </button>
      </div>
      <div class="module-body" v-show="show.area">
        <div id="areaChart" class="chart-item"></div>
      </div>
    </div>
    <!-- 销量趋势与预测 -->
    <div class="module">
      <div class="module-header">
        <div class="title-row">
          <span>销量趋势与预测</span>
          <select v-model="trendGranularity" @change="handleTrendChange">
            <option value="day">按日</option>
            <option value="week">按周</option>
            <option value="month">按月</option>
          </select>
        </div>
        <button class="blue-btn" @click="triggerForecast">生成预测</button>
        <button class="blue-btn" @click="show.trend = !show.trend">
          {{ show.trend ? '收起' : '展开' }}
        </button>
      </div>
      <div class="module-body" v-show="show.trend">
        <div v-if="forecastStatus === 'pending'" class="loading">预测任务执行中...</div>
        <div v-else-if="forecastStatus === 'failed'" class="error">预测生成失败</div>
        <div v-else id="trendChart" class="chart-item"></div>
      </div>
    </div>
    <!-- RFM 用户价值分层 -->
    <div class="module">
      <div class="module-header">
        <span>RFM 用户价值分层</span>
        <button class="blue-btn" @click="triggerRFM">计算RFM</button>
        <button class="blue-btn" @click="show.rfm = !show.rfm">
          {{ show.rfm ? '收起' : '展开' }}
        </button>
      </div>
      <div class="module-body" v-show="show.rfm">
        <div v-if="rfmStatus === 'pending'" class="loading">RFM计算中...</div>
        <div v-else-if="rfmStatus === 'failed'" class="error">RFM计算失败</div>
        <div v-else>
          <div v-for="(item, idx) in rfmData" :key="idx" class="rfm-item">
            {{ item.segment }}：{{ item.userCount }}人 ({{ item.percent }}%)，平均消费¥{{ item.avgMonetary }}
          </div>
        </div>
      </div>
    </div>
    <!-- 商品关联推荐 -->
    <div class="module">
      <div class="module-header">
        <span>商品关联推荐</span>
        <button class="blue-btn" @click="triggerAssociation">计算关联规则</button>
        <button class="blue-btn" @click="show.recommend = !show.recommend">
          {{ show.recommend ? '收起' : '展开' }}
        </button>
      </div>
      <div class="module-body" v-show="show.recommend">
        <div v-if="associationStatus === 'pending'" class="loading">关联规则计算中...</div>
        <div v-else-if="associationStatus === 'failed'" class="error">关联规则计算失败</div>
        <div v-else>
          <div v-for="(item, idx) in recommendData" :key="idx" class="recommend-item">
            {{ item.antecedentNames.join(' + ') }} → {{ item.consequentNames.join(' + ') }}
            (置信度: {{ (item.confidence * 100).toFixed(2) }}%, 提升度: {{ item.lift.toFixed(2) }})
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'
// 接口配置
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'
axios.defaults.baseURL = API_BASE
// 响应式数据
const data = reactive({
  totalSales: 0,
  totalOrders: 0,
  totalUsers: 0,
  avgOrderValue: 0,
  compareLastPeriod: null
})
const rfmData = ref([])
const recommendData = ref([])
const categoryList = ref([])
const provinceList = ref([])
const selectedArea = ref('全国')
// 修复初始值
const rankType = ref('salesVolume')
const show = reactive({
  csv: true, rank: true, cate: true, area: true, trend: true, rfm: true, recommend: true
})
const csvFile = ref(null)
const chartIns = reactive({ rank: null, cate: null, area: null, trend: null })
// 时间范围
const dateRange = reactive({
  startDate: '',
  endDate: ''
})
// 筛选额外变量
const rankCategory = ref('')
const trendGranularity = ref('month')
// 上传结果
const uploadResult = ref(null)
// 任务状态
const rfmStatus = ref('idle')
const associationStatus = ref('idle')
const forecastStatus = ref('idle')
const taskPollingTimer = ref(null)
// 图表专用数据
const rankData = ref([])
const areaData = ref({})
const trendData = ref({
  x: [],
  history: [],
  predict: []
})
const cateData = ref([])

// 统一处理后端响应
const handleApiResponse = async (promise) => {
  try {
    const res = await promise
    if (res.data.code !== 200) {
      throw new Error(res.data.message || '接口请求失败')
    }
    return res.data.data
  } catch (err) {
    console.error(err)
    alert(err.message || '服务器异常')
    return null
  }
}

// 任务轮询
const pollTaskStatus = async (api, batchUuid, successCallback, failCallback) => {
  clearInterval(taskPollingTimer.value)
  taskPollingTimer.value = setInterval(async () => {
    const data = await handleApiResponse(axios.get(`${api}/${batchUuid}`))
    if (!data) return
    if (data.status === 'completed') {
      clearInterval(taskPollingTimer.value)
      successCallback(data)
    } else if (data.status === 'failed') {
      clearInterval(taskPollingTimer.value)
      failCallback()
    }
  }, 2000)
}

// 解析并校验CSV文件（严格匹配指定格式）
const parseAndValidateCSV = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.readAsText(file, 'UTF-8')
    reader.onload = (e) => {
      try {
        const content = e.target.result
        const lines = content.split('\n').filter(line => line.trim())
        if (lines.length === 0) {
          reject({ message: 'CSV文件内容为空' })
          return
        }
        // 校验必填表头
        const headerLine = lines[0].trim()
        const headers = headerLine.split(',').map(h => h.trim())
        const requiredHeaders = [
          'order_id', 'product_id', 'product_name', 'category',
          'unit_price', 'quantity', 'total_amount', 'user_id',
          'province', 'order_date'
        ]
        const missingHeaders = requiredHeaders.filter(h => !headers.includes(h))
        if (missingHeaders.length > 0) {
          reject({
            message: `缺少必填表头：${missingHeaders.join(', ')}`,
            errors: []
          })
          return
        }
        // 逐行校验数据规则
        const errors = []
        const validData = []
        const dateRegex = /^\d{4}-\d{2}-\d{2}$/
        for (let i = 1; i < lines.length; i++) {
          const row = lines[i].trim()
          if (!row) continue
          const cells = row.split(',')
          const rowObj = {}
          headers.forEach((header, idx) => {
            rowObj[header] = cells[idx] ? cells[idx].trim() : ''
          })
          const rowErrors = []
          // 字段规则校验
          if (!rowObj.order_id) rowErrors.push('订单ID不能为空')
          if (!rowObj.product_id || isNaN(Number(rowObj.product_id))) rowErrors.push('商品ID必须为数字')
          if (!rowObj.product_name) rowErrors.push('商品名称不能为空')
          if (!rowObj.category) rowErrors.push('品类不能为空')
          if (!rowObj.unit_price || isNaN(Number(rowObj.unit_price)) || Number(rowObj.unit_price) <= 0) rowErrors.push('单价必须为正数')
          if (!rowObj.quantity || isNaN(Number(rowObj.quantity)) || !Number.isInteger(Number(rowObj.quantity)) || Number(rowObj.quantity) <= 0) rowErrors.push('数量必须为正整数')
          if (rowObj.total_amount === '' || isNaN(Number(rowObj.total_amount)) || Number(rowObj.total_amount) < 0) rowErrors.push('金额必须大于等于0')
          if (!rowObj.user_id || isNaN(Number(rowObj.user_id))) rowErrors.push('用户ID必须为数字')
          if (!rowObj.province) rowErrors.push('省份不能为空')
          if (!rowObj.order_date || !dateRegex.test(rowObj.order_date)) rowErrors.push('订单日期格式必须为 YYYY-MM-DD')
          // 非必填字段默认值
          if (!rowObj.order_status) rowObj.order_status = 'completed'

          if (rowErrors.length > 0) {
            errors.push({ row: i + 1, reason: rowErrors.join('; ') })
          } else {
            validData.push({
              order_id: rowObj.order_id,
              product_id: Number(rowObj.product_id),
              product_name: rowObj.product_name,
              category: rowObj.category,
              unit_price: Number(rowObj.unit_price),
              quantity: Number(rowObj.quantity),
              total_amount: Number(rowObj.total_amount),
              user_id: Number(rowObj.user_id),
              province: rowObj.province,
              city: rowObj.city || '',
              order_date: rowObj.order_date,
              order_status: rowObj.order_status
            })
          }
        }
        if (errors.length > 0) {
          reject({ message: `CSV校验失败，共${errors.length}行数据错误`, errors })
        } else {
          resolve({ message: `CSV校验成功，共${validData.length}行有效数据`, data: validData })
        }
      } catch (err) {
        reject({ message: 'CSV解析失败：' + err.message, errors: [] })
      }
    }
    reader.onerror = () => {
      reject({ message: '文件读取失败', errors: [] })
    }
  })
}

// 统一获取所有数据
async function fetchAllData() {
  // 日期合法性校验
  if (new Date(dateRange.startDate) > new Date(dateRange.endDate)) {
    alert('开始日期不能晚于结束日期！')
    return
  }
  if (!dateRange.startDate || !dateRange.endDate) {
    const end = new Date()
    const start = new Date()
    start.setMonth(end.getMonth() - 3)
    dateRange.startDate = start.toISOString().split('T')[0]
    dateRange.endDate = end.toISOString().split('T')[0]
  }
  // 核心指标
  const kpiData = await handleApiResponse(axios.get('/dashboard/kpis', {
    params: {
      startDate: dateRange.startDate,
      endDate: dateRange.endDate
    }
  }))
  if (kpiData) {
    data.totalSales = kpiData.totalSales
    data.totalOrders = kpiData.totalOrders
    data.totalUsers = kpiData.totalUsers
    data.avgOrderValue = kpiData.avgOrderValue
  }
  await fetchRankData()
  await fetchCategoryData()
  await fetchAreaData()
  await fetchTrendData()
}

// 销售排行数据
async function fetchRankData() {
  const rankRes = await handleApiResponse(axios.get('/sales/ranking', {
    params: {
      rankBy: rankType.value,
      order: 'desc',
      limit: 20,
      category: rankCategory.value,
      startDate: dateRange.startDate,
      endDate: dateRange.endDate
    }
  }))
  if (rankRes) {
    rankData.value = rankRes.rankings
    initRankChart()
  }
}

// 分类分析（单级分类 + 饼图）
async function fetchCategoryData() {
  const cateRes = await handleApiResponse(axios.get('/category/analysis', {
    params: {
      startDate: dateRange.startDate,
      endDate: dateRange.endDate
    }
  }))
  if (cateRes && cateRes.categories) {
    // 后端返回的是对象，需要取 categories 数组
    categoryList.value = cateRes.categories.map(item => item.category)
    cateData.value = cateRes.categories
    initCateChart()
  }
}

// 地域分析
async function fetchAreaData() {
  const areaRes = await handleApiResponse(axios.get('/region/analysis', {
    params: {
      startDate: dateRange.startDate,
      endDate: dateRange.endDate
    }
  }))
  if (areaRes) {
    provinceList.value = areaRes.regions.map(item => item.province)
    areaData.value = {
      全国: {
        x: areaRes.regions.map(item => item.province),
        y: areaRes.regions.map(item => item.salesAmount)
      }
    }
    for (const p of provinceList.value) {
      const detail = await handleApiResponse(axios.get(`/region/detail/${p}`, {
        params: { startDate: dateRange.startDate, endDate: dateRange.endDate }
      }))
      if (detail) {
        areaData.value[p] = {
          x: detail.cities.map(item => item.city),
          y: detail.cities.map(item => item.salesAmount)
        }
      }
    }
    initAreaChart()
  }
}

// 趋势数据
async function fetchTrendData() {
  const trendRes = await handleApiResponse(axios.get('/dashboard/trend', {
    params: {
      startDate: dateRange.startDate,
      endDate: dateRange.endDate,
      granularity: trendGranularity.value
    }
  }))
  if (trendRes) {
    trendData.value = {
      x: trendRes.map(item => item.period),
      history: trendRes.map(item => item.sales),
      predict: []
    }
    initTrendChart()
  }
}

// CSV文件选择
function selectFile(e) {
  csvFile.value = e.target.files[0]
}

// CSV上传
async function uploadCSV() {
  if (!csvFile.value) return alert('请选择CSV文件')
  try {
    uploadResult.value = null
    const validateResult = await parseAndValidateCSV(csvFile.value)
    const fd = new FormData()
    fd.append('file', csvFile.value)
    const res = await axios.post('/upload/csv', fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    if (res.data.code === 200) {
      uploadResult.value = { message: '上传成功！数据已导入系统', data: { errors: [] } }
      alert('上传成功！正在刷新数据...')
      // 增加延迟，确保后端数据落地（根据后端处理速度调整，如1-2秒）
      setTimeout(async () => {
        await fetchAllData()
        // 强制刷新所有图表（兜底）
        refreshAllCharts()
      }, 1000) 
    } else {
      uploadResult.value = res.data
      alert(res.data.message)
    }
  } catch (validateError) {
    uploadResult.value = {
      message: validateError.message,
      data: validateError.errors || []
    }
  }
}

// 排行类型切换
function handleRankChange() {
  fetchRankData()
}
// 地域切换
function handleAreaChange() {
  initAreaChart()
}
// 趋势粒度切换
function handleTrendChange() {
  fetchTrendData()
}

// 图表刷新
function refreshAllCharts() {
  initRankChart()
  initCateChart()
  initAreaChart()
  initTrendChart()
}

// 地域柱状图
function initAreaChart() {
  const el = document.getElementById('areaChart')
  if (!el) return
  chartIns.area?.dispose()
  chartIns.area = echarts.init(el)
  const current = selectedArea.value
  const data = areaData.value[current]
  chartIns.area.setOption({
    title: { text: `${current}销售分布`, left: 'center' },
    xAxis: { data: data.x },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: data.y, itemStyle: { color: '#1677ff' } }]
  })
}

// 销量趋势图
function initTrendChart() {
  const el = document.getElementById('trendChart')
  if (!el) return
  chartIns.trend?.dispose()
  chartIns.trend = echarts.init(el)
  chartIns.trend.setOption({
    title: { text: '销量趋势与预测', left: 'center' },
    xAxis: { data: trendData.value.x },
    yAxis: { type: 'value' },
    series: [
      { name: '历史销量', type: 'line', data: trendData.value.history },
      { name: '预测销量', type: 'line', data: trendData.value.predict, lineStyle: { type: 'dashed' } }
    ]
  })
}

// ========== 核心修改：商品销售排行【横向柱状图（条形图）】 ==========
function initRankChart() {
  const el = document.getElementById('rankChart')
  if (!el || !rankData.value.length) return
  chartIns.rank?.dispose()
  chartIns.rank = echarts.init(el)

  // 1. 先将原始数据按销量/销售额降序排序（确保数据本身是从高到低）
  const sortedRankData = [...rankData.value].sort((a, b) => {
    const valueA = rankType.value === 'salesVolume' ? a.salesVolume : a.salesAmount
    const valueB = rankType.value === 'salesVolume' ? b.salesVolume : b.salesAmount
    return valueB - valueA // 降序排序
  })

  // 2. 基于排序后的数据生成XY轴（反向数组，让ECharts从上到下显示高→低）
  const yData = sortedRankData.map(item => item.productName).reverse()
  const xData = sortedRankData.map(item =>
    rankType.value === 'salesVolume' ? item.salesVolume : item.salesAmount
  ).reverse()

  const chartTitle = rankType.value === 'salesVolume' ? '商品销量排行' : '商品销售额排行'

  const option = {
    title: { text: chartTitle, left: 'center' },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true // 防止文字被截断
    },
    // 横向柱状图核心配置：x轴为数值，y轴为分类
    xAxis: {
      type: 'value',
      name: rankType.value === 'salesVolume' ? '销量' : '销售额(元)'
    },
    yAxis: {
      type: 'category',
      data: yData,
      axisLabel: {
        fontSize: 12
      }
    },
    series: [
      {
        name: rankType.value === 'salesVolume' ? '销量' : '销售额',
        type: 'bar',
        data: xData,
        itemStyle: { color: '#1677ff' },
        barWidth: '60%'
      }
    ]
  }
  chartIns.rank.setOption(option)
}

// 分类饼图（单级分类占比）
function initCateChart() {
  const el = document.getElementById('cateChart')
  if (!el || !cateData.value.length) return
  chartIns.cate?.dispose()
  chartIns.cate = echarts.init(el)
  chartIns.cate.setOption({
    title: { text: '商品分类销售占比', left: 'center' },
    tooltip: { trigger: 'item', formatter: '{a} <br/>{b}: {c} ({d}%)' },
    legend: {
      orient: 'vertical',
      left: 'left',
      data: cateData.value.map(item => item.category)
    },
    series: [{
      name: '销售额',
      type: 'pie',
      radius: ['30%', '70%'],
      data: cateData.value.map(item => ({
        name: item.category,
        value: item.salesAmount
      })),
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      },
      label: {
        show: true,
        formatter: '{b}: {c} ({d}%)'
      }
    }]
  })
}

// RFM计算
async function triggerRFM() {
  rfmStatus.value = 'pending'
  const task = await handleApiResponse(axios.post('/rfm/trigger', {
    startDate: dateRange.startDate,
    endDate: dateRange.endDate,
    recencyBaseDate: dateRange.endDate,
    params: { scoringMethod: 'quantile' }
  }))
  if (task) {
    pollTaskStatus('/rfm/status', task.batchUuid, async () => {
      const res = await handleApiResponse(axios.get('/rfm/result'))
      if (res) {
        rfmData.value = res.segments
        rfmStatus.value = 'completed'
      } else rfmStatus.value = 'failed'
    }, () => rfmStatus.value = 'failed')
  } else rfmStatus.value = 'failed'
}

// 关联规则计算
async function triggerAssociation() {
  associationStatus.value = 'pending'
  const task = await handleApiResponse(axios.post('/association/trigger', {
    startDate: dateRange.startDate,
    endDate: dateRange.endDate,
    params: { minSupport: 0.01, minConfidence: 0.3, minLift: 1.0, maxLength: 3 }
  }))
  if (task) {
    pollTaskStatus('/association/status', task.batchUuid, async () => {
      const res = await handleApiResponse(axios.get('/association/result'))
      if (res) {
        recommendData.value = res.rules
        associationStatus.value = 'completed'
      } else associationStatus.value = 'failed'
    }, () => associationStatus.value = 'failed')
  } else associationStatus.value = 'failed'
}

// 销量预测
async function triggerForecast() {
  forecastStatus.value = 'pending'
  const task = await handleApiResponse(axios.post('/forecast/trigger', {
    startDate: dateRange.startDate,
    endDate: dateRange.endDate,
    forecastDays: 30,
    targetProductIds: [],
    params: { model: 'prophet' }
  }))
  if (task) {
    pollTaskStatus('/forecast/status', task.batchUuid, async () => {
      const res = await handleApiResponse(axios.get('/forecast/result'))
      if (res && res.products.length) {
        const item = res.products[0]
        trendData.value.predict = item.forecasts.map(d => d.predictedQty)
        trendData.value.x = [...trendData.value.x, ...item.forecasts.map(d => d.date)]
        initTrendChart()
        forecastStatus.value = 'completed'
      } else forecastStatus.value = 'failed'
    }, () => forecastStatus.value = 'failed')
  } else forecastStatus.value = 'failed'
}

// 生命周期
onMounted(() => {
  const today = new Date()
  const threeMonthsAgo = new Date()
  threeMonthsAgo.setMonth(today.getMonth() - 3)
  dateRange.startDate = threeMonthsAgo.toISOString().split('T')[0]
  dateRange.endDate = today.toISOString().split('T')[0]
  fetchAllData()
  window.addEventListener('resize', () => Object.values(chartIns).forEach(i => i?.resize()))
})

onUnmounted(() => {
  clearInterval(taskPollingTimer.value)
  Object.values(chartIns).forEach(i => i?.dispose())
  window.removeEventListener('resize', () => Object.values(chartIns).forEach(i => i?.resize()))
})
</script>

<style scoped>
.wrap {
  background: #f5f7fa;
  padding: 25px;
  width: 80vw;
  max-width: 1400px;
  margin: 0 auto;
}
h1 {
  text-align: center;
  margin-bottom: 20px;
}
.module {
  background: white;
  border-radius: 10px;
  margin-bottom: 20px;
  box-shadow: 0 1px 6px #00000010;
  overflow: hidden;
}
.module-header {
  padding: 14px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 16px;
}
.blue-btn {
  background: #1677ff;
  color: white;
  border: none;
  padding: 5px 12px;
  border-radius: 4px;
  cursor: pointer;
}
.module-body {
  padding: 20px;
}
.chart-item {
  width: 100%;
  height: 440px;
}
.card-group {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.card {
  background: white;
  padding: 20px;
  border-radius: 10px;
  text-align: center;
}
.card h3 {
  font-size: 15px;
  color: #666;
  margin-bottom: 6px;
}
.card .num {
  font-size: 24px;
  font-weight: bold;
  color: #1677ff;
}
select {
  padding: 4px 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.rank-chart-container {
  height: 380px;
  overflow-y: auto;
}
.rfm-item, .recommend-item {
  line-height: 1.8;
  font-size: 14px;
}
.date-filter {
  background: white;
  padding: 16px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  gap: 12px;
  align-items: center;
}
.date-filter input[type="date"] {
  padding: 4px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.upload-result {
  margin-top: 12px;
  padding: 8px;
  border-radius: 4px;
  background: #f0f8ff;
  color: #1677ff;
}
.loading {
  text-align: center;
  padding: 20px;
  color: #1677ff;
}
.error {
  text-align: center;
  padding: 20px;
  color: #ff4d4f;
}
</style>
