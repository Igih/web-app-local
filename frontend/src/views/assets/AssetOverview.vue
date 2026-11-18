<template>
  <el-container class="asset-overview-page">
    <el-card>
      <template #header>
        <span>图像资源统计</span>
      </template>
      <el-row :gutter="12">
        <el-col v-for="card in totals" :key="card.label" :span="4">
          <el-statistic :title="card.label" :value="card.value" />
        </el-col>
      </el-row>
      <el-table :data="categories" class="stats-table">
        <el-table-column prop="display_name" label="类别" width="120" />
        <el-table-column label="实拍·可见光">
          <template #default="{ row }">{{ row.combinations.photo_visible }}</template>
        </el-table-column>
        <el-table-column label="实拍·红外">
          <template #default="{ row }">{{ row.combinations.photo_infrared }}</template>
        </el-table-column>
        <el-table-column label="手绘·可见光">
          <template #default="{ row }">{{ row.combinations.hand_drawn_visible }}</template>
        </el-table-column>
        <el-table-column label="手绘·红外">
          <template #default="{ row }">{{ row.combinations.hand_drawn_infrared }}</template>
        </el-table-column>
        <el-table-column prop="photo_unspecified" label="实拍·未指定光谱" />
        <el-table-column prop="hand_drawn_unspecified" label="手绘·未指定光谱" />
        <el-table-column prop="type_unspecified" label="类型未指定" />
      </el-table>
    </el-card>
  </el-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const stats = ref(null)

const categories = computed(() => stats.value?.categories || [])
const totals = computed(() => {
  const data = stats.value?.totals
  if (!data) return []
  return [
    { label: '唯一图片数', value: data.unique_images },
    { label: '源文件数', value: data.source_files },
    { label: '重复数', value: data.duplicates },
    { label: '损坏数', value: data.damaged },
    { label: '冲突待审数', value: data.conflicts },
  ]
})

onMounted(async () => {
  try {
    const response = await axios.get('/api/assets/overview/stats')
    stats.value = response.data
  } catch (error) {
    ElMessage.error('加载统计失败')
  }
})
</script>

<style scoped>
.asset-overview-page {
  display: block;
}

.stats-table {
  margin-top: 20px;
}
</style>
