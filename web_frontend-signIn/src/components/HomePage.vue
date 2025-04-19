<template>
  <div class="home-content">
    <!-- 主内容 -->
    <div class="hero-section">
      <h1>Everything you need to build and deploy computer vision applications.</h1>
      <p>Used by over 1 million engineers to create datasets, train models, and deploy to production.</p>
    </div>

    <!-- Add chart section -->
    <div class="charts-section">
      <div class="chart-container">
        <h2>Dataset Distribution</h2>
        <div class="charts">
          <div class="pie-chart">
            <canvas id="pieChart"></canvas>
          </div>
          <div class="bar-chart">
            <canvas id="barChart"></canvas>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import Chart from 'chart.js/auto'
import ChartDataLabels from 'chartjs-plugin-datalabels'
import { ElMessage } from 'element-plus'

Chart.register(ChartDataLabels)

const chartData = ref({ categories: [], counts: [] })

const fetchChartData = async () => {
  try {
    const response = await axios.get('/api/categories_show')
    const categoriesData = response.data.categories_show
    // 创建包含 category 和 count 的数组用于排序
    let dataArray = categoriesData.map(item => ({
      category: item.category,
      count: item.count
    }))
    // 按 count 从大到小排序
    dataArray.sort((a, b) => b.count - a.count)
    // 更新 chartData
    chartData.value.categories = dataArray.map(item => item.category)
    chartData.value.counts = dataArray.map(item => item.count)

    const total = chartData.value.counts.reduce((sum, count) => sum + count, 0)

    const backgroundPlugin = {
      id: 'customCanvasBackgroundColor',
      beforeDraw: (chart) => {
        const ctx = chart.canvas.getContext('2d')
        ctx.save()
        ctx.globalCompositeOperation = 'destination-over'
        ctx.fillStyle = '#f5f7fa'
        ctx.fillRect(0, 0, chart.width, chart.height)
        ctx.restore()
      }
    }

    Chart.register(backgroundPlugin)

    // 饼状图（保持不变）
    const pieCtx = document.getElementById('pieChart').getContext('2d')
    new Chart(pieCtx, {
      type: 'pie',
      data: {
        labels: chartData.value.categories,
        datasets: [{
          data: chartData.value.counts.map(count => ((count / total) * 100).toFixed(1)),
          backgroundColor: [
            '#FF6384', // 红色系 - 已有
            '#36A2EB', // 蓝色系 - 已有
            '#FFCE56', // 黄色系 - 已有
            '#4BC0C0', // 青色系 - 已有
            '#9966FF', // 紫色系 - 已有
            '#FF9F40', // 橙色系 - 已有
            '#C9CBCF', // 灰色系 - 已有
            '#E57373', // 红色系 - 浅红
            '#64B5F6', // 蓝色系 - 浅蓝
            '#FFD54F', // 黄色系 - 浅黄
            '#80DEEA', // 青色系 - 浅青
            '#B388FF', // 紫色系 - 浅紫
            '#FFB74D', // 橙色系 - 浅橙
            '#A5D6A7', // 绿色系 - 浅绿
            '#F06292', // 粉色系 - 深粉
            '#4FC3F7', // 蓝色系 - 中蓝
            '#FFCA28', // 黄色系 - 中黄
            '#26A69A', // 青色系 - 中青
            '#9575CD', // 紫色系 - 中紫
            '#FF8A65', // 橙色系 - 中橙
            '#81C784', // 绿色系 - 中绿
            '#EC407A', // 粉色系 - 中粉
            '#42A5F5', // 蓝色系 - 亮蓝
            '#FFEE58', // 黄色系 - 亮黄
            '#4DD0E1', // 青色系 - 亮青
            '#7E57C2', // 紫色系 - 深紫
            '#FF7043', // 橙色系 - 深橙
            '#66BB6A', // 绿色系 - 深绿
            '#F06292', // 粉色系 - 亮粉
            '#0288D1', // 蓝色系 - 深蓝
            '#FDD835'  // 黄色系 - 深黄
          ]
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          customCanvasBackgroundColor: true,
          legend: {
            position: 'top',
            labels: {
              font: { size: 16 }
            }
          },
          tooltip: {
            callbacks: {
              label: (context) => `${context.label}: ${context.raw}%`
            }
          },
          datalabels: {
            color: '#fff',
            formatter: (value) => `${value}%`,
            font: {
              weight: 'bold',
              size: 18
            }
          }
        }
      }
    })

    // 柱状图（横向）
    const barCtx = document.getElementById('barChart').getContext('2d')
    new Chart(barCtx, {
      type: 'bar',
      data: {
        labels: chartData.value.categories,
        datasets: [{
          label: 'Dataset Count',
          data: chartData.value.counts,
          backgroundColor: [
            '#FF6384', // 红色系 - 已有
            '#36A2EB', // 蓝色系 - 已有
            '#FFCE56', // 黄色系 - 已有
            '#4BC0C0', // 青色系 - 已有
            '#9966FF', // 紫色系 - 已有
            '#FF9F40', // 橙色系 - 已有
            '#C9CBCF', // 灰色系 - 已有
            '#E57373', // 红色系 - 浅红
            '#64B5F6', // 蓝色系 - 浅蓝
            '#FFD54F', // 黄色系 - 浅黄
            '#80DEEA', // 青色系 - 浅青
            '#B388FF', // 紫色系 - 浅紫
            '#FFB74D', // 橙色系 - 浅橙
            '#A5D6A7', // 绿色系 - 浅绿
            '#F06292', // 粉色系 - 深粉
            '#4FC3F7', // 蓝色系 - 中蓝
            '#FFCA28', // 黄色系 - 中黄
            '#26A69A', // 青色系 - 中青
            '#9575CD', // 紫色系 - 中紫
            '#FF8A65', // 橙色系 - 中橙
            '#81C784', // 绿色系 - 中绿
            '#EC407A', // 粉色系 - 中粉
            '#42A5F5', // 蓝色系 - 亮蓝
            '#FFEE58', // 黄色系 - 亮黄
            '#4DD0E1', // 青色系 - 亮青
            '#7E57C2', // 紫色系 - 深紫
            '#FF7043', // 橙色系 - 深橙
            '#66BB6A', // 绿色系 - 深绿
            '#F06292', // 粉色系 - 亮粉
            '#0288D1', // 蓝色系 - 深蓝
            '#FDD835'  // 黄色系 - 深黄
          ]
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          customCanvasBackgroundColor: true,
          legend: { display: false },
          datalabels: {
            anchor: 'end', // 标签锚点在柱子末端
            align: 'end',  // 标签对齐到柱子外侧
            offset: 8,     // 增加偏移量，避免数值被截断
            formatter: (value) => value,
            color: '#000',
            font: {
              weight: 'bold',
              size: 16
            }
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            // 动态设置最大值，留出空间显示标签
            max: Math.max(...chartData.value.counts) * 1.2, // 增加 20% 的空间
            title: {
              display: true,
              text: 'Count',
              font: { size: 16 }
            },
            ticks: {
              font: { size: 14 },
              padding: 10 // 增加刻度与图表边缘的内边距
            }
          },
          y: {
            title: {
              display: true,
              text: 'Categories',
              font: { size: 16 }
            },
            ticks: { font: { size: 14 } }
          }
        }
      }
    })
  } catch (error) {
    console.error('Failed to fetch chart data:', error)
    ElMessage.error('Failed to load chart data')
  }
}

onMounted(() => {
  fetchChartData()
})
</script>

<style scoped>
.home-content {
  background-color: #f5f7fa;
  font-family: 'Arial', sans-serif;
}

.hero-section {
  text-align: center;
  padding: 50px 20px;
}

.hero-section h1 {
  font-size: 48px;
  font-weight: bold;
  color: #1f2a44;
  margin-bottom: 20px;
}

.hero-section p {
  font-size: 18px;
  color: #606266;
  margin-bottom: 30px;
}

.charts-section {
  padding: 60px 80px;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.chart-container {
  max-width: 1400px;
  margin: 0 auto;
  text-align: center;
}

.chart-container h2 {
  margin-bottom: 30px;
  font-size: 32px;
  font-weight: bold;
}

.charts {
  display: flex;
  justify-content: space-between;
  gap: 60px;
}

.pie-chart,
.bar-chart {
  flex: 1;
  max-width: 800px;
  padding: 0;
  margin: 0;
}

.pie-chart canvas,
.bar-chart canvas {
  width: 100% !important;
  height: 400px !important;
}

@media (max-width: 768px) {
  .charts {
    flex-direction: column;
    align-items: center;
    gap: 40px;
  }

  .pie-chart,
  .bar-chart {
    max-width: 100%;
  }

  .pie-chart canvas,
  .bar-chart canvas {
    height: 300px !important;
  }
}
</style>