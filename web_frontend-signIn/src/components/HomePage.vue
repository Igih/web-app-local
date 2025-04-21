<template>
  <div class="home-content">
    <!-- 主内容 -->
    <div class="hero-section">
      <h1>新一代自动目标识别数据管理系统</h1>
      <p>中国科学院光电信息处理重点实验室</p>
    </div>

    <!-- Add chart section -->
    <div class="charts-section">
      <div class="chart-container">
        <!-- <h2>Dataset Distribution</h2> -->
        <div class="charts">
          <div class="pie-chart">
            <div class="pie-chart-wrapper">
              <!-- Custom legend on the left -->
              <div class="custom-legend">
                <div v-for="(category, index) in chartData.categories" :key="index" class="legend-item">
                  <span class="legend-color" :style="{ backgroundColor: colors[index] }"></span>
                  <span class="legend-label">{{ category }}</span>
                  <span class="legend-percentage">{{ percentages[index] }}%</span>
                </div>
              </div>
              <!-- Pie chart canvas -->
              <canvas id="pieChart"></canvas>
            </div>
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
const percentages = ref([])
const colors = [
  '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF',
  '#E57373', '#64B5F6', '#FFD54F', '#80DEEA', '#B388FF', '#FFB74D', '#A5D6A7',
  '#F06292', '#4FC3F7', '#FFCA28', '#26A69A', '#9575CD', '#FF8A65', '#81C784',
  '#EC407A', '#42A5F5', '#FFEE58', '#4DD0E1', '#7E57C2', '#FF7043', '#66BB6A',
  '#F06292', '#0288D1', '#FDD835'
]

const fetchChartData = async () => {
  try {
    const response = await axios.get('/api/categories_show')
    const categoriesData = response.data.categories_show
    let dataArray = categoriesData.map(item => ({
      category: item.category,
      count: item.count
    }))
    dataArray.sort((a, b) => b.count - a.count)
    chartData.value.categories = dataArray.map(item => item.category)
    chartData.value.counts = dataArray.map(item => item.count)

    const total = chartData.value.counts.reduce((sum, count) => sum + count, 0)
    percentages.value = chartData.value.counts.map(count => ((count / total) * 100).toFixed(1))

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

    // Pie chart
    const pieCtx = document.getElementById('pieChart').getContext('2d')
    new Chart(pieCtx, {
      type: 'pie',
      data: {
        labels: chartData.value.categories,
        datasets: [{
          data: chartData.value.counts,
          backgroundColor: colors
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          customCanvasBackgroundColor: true,
          legend: {
            display: false // Disable default legend
          },
          tooltip: {
            callbacks: {
              label: (context) => `${context.label}: ${percentages.value[context.dataIndex]}%`
            }
          },
          datalabels: {
            color: '#fff',
            formatter: (value, context) => {
              const percentage = parseFloat(percentages.value[context.dataIndex])
              return percentage >= 5 ? `${percentage}%` : ''
            },
            font: {
              weight: 'bold',
              size: 18
            }
          }
        }
      }
    })

    // Bar chart (unchanged)
    const barCtx = document.getElementById('barChart').getContext('2d')
    new Chart(barCtx, {
      type: 'bar',
      data: {
        labels: chartData.value.categories,
        datasets: [{
          label: 'Dataset Count',
          data: chartData.value.counts,
          backgroundColor: colors
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
            anchor: 'end',
            align: 'end',
            offset: 8,
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
            max: Math.max(...chartData.value.counts) * 1.2,
            title: {
              display: true,
              text: 'Count',
              font: { size: 16 }
            },
            ticks: {
              font: { size: 14 },
              padding: 10
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

.pie-chart-wrapper {
  display: flex;
  align-items: center;
}

.custom-legend {
  display: flex;
  flex-direction: column;
  margin-right: 20px;
  max-width: 300px;
}

.legend-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.legend-color {
  width: 20px;
  height: 20px;
  display: inline-block;
  margin-right: 10px;
}

.legend-label {
  font-size: 14px;
  color: #333;
  flex: 1;
}

.legend-percentage {
  font-size: 14px;
  font-weight: bold;
  color: #333;
  margin-left: 10px;
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

  .pie-chart-wrapper {
    flex-direction: column;
    align-items: center;
  }

  .custom-legend {
    margin-right: 0;
    margin-bottom: 20px;
    max-width: 100%;
    align-items: flex-start;
  }

  .pie-chart canvas,
  .bar-chart canvas {
    height: 300px !important;
  }
}
</style>