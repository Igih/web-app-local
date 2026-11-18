<template>
  <el-container class="asset-import-page">
    <el-card>
      <template #header>
        <span>图像资源导入</span>
      </template>

      <el-form label-width="120px" @submit.prevent="submitScan">
        <el-form-item label="图片路径" required>
          <el-input v-model="form.image_path" placeholder="/home/linux/Downloads/..." />
        </el-form-item>
        <el-form-item label="花卉类别" required>
          <el-select v-model="form.category" placeholder="请选择类别">
            <el-option
              v-for="category in categories"
              :key="category.id"
              :label="category.display_name"
              :value="category.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="标注路径">
          <el-input v-model="form.annotation_path" placeholder="可选，文件或目录" />
        </el-form-item>
        <el-form-item label="一级类型">
          <el-select v-model="form.capture_type" clearable placeholder="未指定">
            <el-option label="实拍" value="photo" />
            <el-option label="手绘" value="hand_drawn" />
          </el-select>
        </el-form-item>
        <el-form-item label="二级类型">
          <el-select
            v-model="form.spectral_type"
            clearable
            :disabled="!form.capture_type"
            placeholder="未指定"
          >
            <el-option label="可见光" value="visible" />
            <el-option label="红外" value="infrared" />
          </el-select>
        </el-form-item>
        <el-form-item label="自定义标签">
          <el-select
            v-model="form.tags"
            multiple
            filterable
            allow-create
            :multiple-limit="5"
            placeholder="最多 5 个"
          />
        </el-form-item>
        <el-form-item label="递归扫描">
          <el-switch v-model="form.recursive" />
        </el-form-item>
        <el-form-item label="批次备注">
          <el-input v-model="form.batch_name" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading">扫描预览</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="preview" class="preview-card">
      <template #header>
        <span>扫描预览</span>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="批次号">{{ preview.batch_id || batchId }}</el-descriptions-item>
        <el-descriptions-item label="图片数量">{{ preview.image_count }}</el-descriptions-item>
        <el-descriptions-item label="异常数量">{{ preview.issue_count }}</el-descriptions-item>
        <el-descriptions-item label="标注匹配">
          {{ preview.annotation_matching?.matched || 0 }} 已匹配 /
          {{ preview.annotation_matching?.ambiguous || 0 }} 歧义 /
          {{ preview.annotation_matching?.unmatched || 0 }} 未匹配
        </el-descriptions-item>
      </el-descriptions>
      <el-button type="success" class="confirm-button" @click="confirm">确认并加入队列</el-button>
    </el-card>
  </el-container>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  confirmAssetImport,
  getAssetCategories,
  getAssetImportPreview,
  scanAssetImport,
} from '@/services/assetImportService'

const categories = ref([])
const loading = ref(false)
const preview = ref(null)
const batchId = ref(null)

const form = reactive({
  image_path: '',
  category: '',
  annotation_path: '',
  capture_type: '',
  spectral_type: '',
  tags: [],
  recursive: true,
  batch_name: '',
})

const submitScan = async () => {
  loading.value = true
  preview.value = null
  try {
    const payload = {
      ...form,
      capture_type: form.capture_type || null,
      spectral_type: form.spectral_type || null,
    }
    const result = await scanAssetImport(payload)
    batchId.value = result.batch_id
    preview.value = result
    ElMessage.success('扫描完成')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '扫描失败')
  } finally {
    loading.value = false
  }
}

const confirm = async () => {
  try {
    const result = await confirmAssetImport(batchId.value)
    ElMessage.success(result.message || '已加入导入队列')
    preview.value = null
    batchId.value = null
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '确认失败')
  }
}

onMounted(async () => {
  try {
    categories.value = await getAssetCategories()
  } catch (error) {
    ElMessage.error('加载资产类别失败')
  }
})
</script>

<style scoped>
.asset-import-page {
  display: block;
}

.preview-card {
  margin-top: 20px;
}

.confirm-button {
  margin-top: 16px;
}
</style>
