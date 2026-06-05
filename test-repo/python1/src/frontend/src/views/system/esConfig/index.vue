<template>
  <div class="inner-page-card es-config-page">
    <div class="config-card">
      <div class="config-card-body">
        <h2 class="page-title">Elasticsearch 环境配置</h2>
        <p class="page-desc">
          配置 Elasticsearch 连接地址与认证信息，用于文档解析与检索。未配置时将回退到环境变量或 config.yml。
        </p>

        <a-form :model="form" layout="vertical" class="es-form" :label-col="{ span: 24 }" :wrapper-col="{ span: 24 }">
          <a-form-item
            label="Elasticsearch 地址"
            name="elasticsearch_url"
            :rules="[{ required: true, message: '请输入 ES 地址' }]"
          >
            <template #extra>
              <span class="field-extra">仅填写协议与主机端口，例如：http://192.168.10.187:9200，不要包含用户名密码。</span>
            </template>
            <a-input v-model:value="form.elasticsearch_url" placeholder="http://192.168.10.187:9200" allow-clear />
          </a-form-item>

          <a-form-item label="用户名" name="elasticsearch_username">
            <a-input v-model:value="form.elasticsearch_username" placeholder="elastic" allow-clear />
          </a-form-item>

          <a-form-item label="密码" name="elasticsearch_password">
            <a-input-password
              v-model:value="form.elasticsearch_password"
              placeholder="请输入密码"
              allow-clear
              autocomplete="off"
            />
          </a-form-item>

          <a-form-item label="默认索引名（可选）" name="linkrag_es_index">
            <template #extra>
              <span class="field-extra"
                >实际写入按各知识库的「ES 索引名 (es_id)」；此处仅作默认/兼容 linkrag config.yml，可不填。</span
              >
            </template>
            <a-input v-model:value="form.linkrag_es_index" placeholder="可选，如 poc" allow-clear />
          </a-form-item>

          <a-form-item label="解析服务地址（可选）" name="linkrag_server_url">
            <template #extra>
              <span class="field-extra"
                >LinkRAG
                解析服务地址，用于创建知识库时同步在解析服务侧创建索引、上传文档时调用解析。不填则完全不连解析服务，仅使用本页 ES
                配置。</span
              >
            </template>
            <a-input
              v-model:value="form.linkrag_server_url"
              placeholder="如 http://127.0.0.1:8000，留空表示不连解析服务"
              allow-clear
            />
          </a-form-item>

          <a-divider orientation="left">Embedding（解析时向量化）</a-divider>
          <a-form-item label="Embedding 服务地址" name="embedding_base_url">
            <template #extra>
              <span class="field-extra"
                >解析文档时用于文本向量化，与 config.yml 中 embedding.base_url
                一致可防止解析报错。例如：http://192.168.10.187:5002/v1/embeddings</span
              >
            </template>
            <a-input v-model:value="form.embedding_base_url" placeholder="http://192.168.10.187:5002/v1/embeddings" allow-clear />
          </a-form-item>
          <a-form-item label="Embedding 模型（可选）" name="embedding_model">
            <template #extra>
              <span class="field-extra"
                >与解析服务侧模型名一致，如 Qwen3-Embedding-0.6B。不填时解析服务使用 config.yml 默认值。</span
              >
            </template>
            <a-input v-model:value="form.embedding_model" placeholder="Qwen3-Embedding-0.6B" allow-clear />
          </a-form-item>
        </a-form>
      </div>

      <div class="config-card-footer">
        <a-space>
          <a-button type="primary" :loading="saving" @click="onSave"> <SaveOutlined /> 保存 </a-button>
          <a-button @click="loadConfig"> 重置 </a-button>
        </a-space>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { message } from "ant-design-vue";
import { SaveOutlined } from "@ant-design/icons-vue";
import { getEsConfig, updateEsConfig } from "@/api/modules/esConfig";

const form = ref({
  elasticsearch_url: "",
  elasticsearch_username: "",
  elasticsearch_password: "",
  linkrag_es_index: "linkrag",
  linkrag_server_url: "",
  embedding_base_url: "",
  embedding_model: ""
});

const saving = ref(false);

async function loadConfig() {
  try {
    const data = await getEsConfig();
    if (data && typeof data === "object") {
      form.value = {
        elasticsearch_url: data.elasticsearch_url ?? "",
        elasticsearch_username: data.elasticsearch_username ?? "",
        elasticsearch_password: data.elasticsearch_password ?? "",
        linkrag_es_index: data.linkrag_es_index ?? "linkrag",
        linkrag_server_url: data.linkrag_server_url ?? "",
        embedding_base_url: data.embedding_base_url ?? "",
        embedding_model: data.embedding_model ?? ""
      };
    }
  } catch (e) {
    console.error("加载 ES 配置失败:", e);
    message.error("加载配置失败");
  }
}

async function onSave() {
  if (!form.value.elasticsearch_url?.trim()) {
    message.warning("请填写 Elasticsearch 地址");
    return;
  }
  saving.value = true;
  try {
    await updateEsConfig({
      elasticsearch_url: form.value.elasticsearch_url.trim() || null,
      elasticsearch_username: form.value.elasticsearch_username?.trim() || null,
      elasticsearch_password: form.value.elasticsearch_password || null,
      linkrag_es_index: form.value.linkrag_es_index?.trim() || null,
      linkrag_server_url: form.value.linkrag_server_url?.trim() || null,
      embedding_base_url: form.value.embedding_base_url?.trim() || null,
      embedding_model: form.value.embedding_model?.trim() || null
    });
    message.success("ES 环境配置已保存");
  } catch (e) {
    message.error("保存失败: " + (e.response?.data?.detail || e.message));
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  loadConfig();
});
</script>

<style scoped lang="scss">
.es-config-page {
  padding: 24px;
}

.config-card {
  max-width: 560px;
  max-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.config-card-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 24px 24px 16px;
}

.config-card-footer {
  flex-shrink: 0;
  padding: 16px 24px 24px;
  border-top: 1px solid #f0f0f0;
  background: #fff;
}

.page-title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: #262626;
}

.page-desc {
  margin: 0 0 24px;
  font-size: 13px;
  color: #8c8c8c;
  line-height: 1.5;
}

.es-form {
  .field-extra {
    font-size: 12px;
    color: #8c8c8c;
  }

  :deep(.ant-form-item-label > label) {
    font-weight: 500;
  }
}
</style>
