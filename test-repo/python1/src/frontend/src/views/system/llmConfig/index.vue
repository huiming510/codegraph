<template>
  <div class="inner-page-card llm-config-page">
    <a-row :gutter="24" class="config-layout">
      <!-- 左侧：设置默认模型 + 添加了的模型 -->
      <a-col :xs="24" :md="10" :lg="9">
        <div class="left-panel">
          <div class="section default-models">
            <h2 class="section-title">设置默认模型</h2>
            <p class="section-desc">请在开始之前完成这些设置</p>
            <a-form
              :model="defaultForm"
              layout="horizontal"
              class="default-form"
              :label-col="{ span: 4 }"
              :wrapper-col="{ span: 20 }"
            >
              <a-form-item label="LLM" name="llm" :rules="[{ required: true, message: '请选择 LLM 模型' }]">
                <template #label>
                  <span><span class="required-star">*</span> LLM</span>
                  <a-tooltip title="大型语言模型，用于对话与生成">
                    <QuestionCircleOutlined class="label-tip" />
                  </a-tooltip>
                </template>
                <a-select
                  v-model:value="defaultForm.llm"
                  placeholder="请选择模型"
                  allow-clear
                  show-search
                  :options="defaultOptions.llm"
                  :field-names="{ label: 'label', value: 'value' }"
                  :filter-option="filterOption"
                  @change="onDefaultModelChange('llm', $event)"
                />
              </a-form-item>
              <a-form-item label="Embedding">
                <template #label>
                  <span>Embedding</span>
                  <a-tooltip title="文本嵌入模型，用于向量化">
                    <QuestionCircleOutlined class="label-tip" />
                  </a-tooltip>
                </template>
                <a-select
                  v-model:value="defaultForm.embedding"
                  placeholder="请选择模型"
                  allow-clear
                  show-search
                  :options="defaultOptions.embedding"
                  :field-names="{ label: 'label', value: 'value' }"
                  :filter-option="filterOption"
                  @change="onDefaultModelChange('embedding', $event)"
                />
              </a-form-item>
              <a-form-item label="VLM">
                <template #label>
                  <span>VLM</span>
                  <a-tooltip title="视觉语言模型，图像理解">
                    <QuestionCircleOutlined class="label-tip" />
                  </a-tooltip>
                </template>
                <a-select
                  v-model:value="defaultForm.vlm"
                  placeholder="请选择模型"
                  allow-clear
                  :options="defaultOptions.vlm"
                  :field-names="{ label: 'label', value: 'value' }"
                  @change="onDefaultModelChange('vlm', $event)"
                />
              </a-form-item>
              <a-form-item label="ASR">
                <template #label>
                  <span>ASR</span>
                  <a-tooltip title="语音识别">
                    <QuestionCircleOutlined class="label-tip" />
                  </a-tooltip>
                </template>
                <a-select
                  v-model:value="defaultForm.asr"
                  placeholder="请选择模型"
                  allow-clear
                  :options="defaultOptions.asr"
                  :field-names="{ label: 'label', value: 'value' }"
                  @change="onDefaultModelChange('asr', $event)"
                />
              </a-form-item>
              <a-form-item label="Rerank">
                <template #label>
                  <span>Rerank</span>
                  <a-tooltip title="文本重排序">
                    <QuestionCircleOutlined class="label-tip" />
                  </a-tooltip>
                </template>
                <a-select
                  v-model:value="defaultForm.rerank"
                  placeholder="请选择模型"
                  allow-clear
                  :options="defaultOptions.rerank"
                  :field-names="{ label: 'label', value: 'value' }"
                  @change="onDefaultModelChange('rerank', $event)"
                />
              </a-form-item>
              <a-form-item label="TTS">
                <template #label>
                  <span>TTS</span>
                  <a-tooltip title="文本转语音">
                    <QuestionCircleOutlined class="label-tip" />
                  </a-tooltip>
                </template>
                <a-select
                  v-model:value="defaultForm.tts"
                  placeholder="请选择模型"
                  allow-clear
                  :options="defaultOptions.tts"
                  :field-names="{ label: 'label', value: 'value' }"
                  @change="onDefaultModelChange('tts', $event)"
                />
              </a-form-item>
            </a-form>
          </div>

          <div class="section added-models">
            <h3 class="subsection-title">已添加的模型</h3>
            <div v-if="addedModelList.length" class="added-list-wrap">
              <div class="added-list">
                <div v-for="row in addedModelList" :key="row.provider + '|' + row.model" class="added-card">
                  <span class="added-icon">{{ row.icon || "🤖" }}</span>
                  <span class="added-name">{{ row.providerLabel }} - {{ row.modelLabel }}</span>
                  <div class="added-card-actions">
                    <a-button
                      type="primary"
                      size="small"
                      class="btn-config"
                      @click="openParamModal(row.provider, row.model, row.modelLabel)"
                    >
                      <SettingOutlined /> 参数配置
                    </a-button>
                    <a-button type="text" size="small" danger class="btn-delete" @click="onDeleteModel(row)">
                      <DeleteOutlined /> 删除
                    </a-button>
                  </div>
                </div>
              </div>
            </div>
            <a-empty v-else description="暂无已添加的模型，可从右侧可选模型添加" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
          </div>
        </div>
      </a-col>

      <!-- 右侧：可选模型 -->
      <a-col :xs="24" :md="14" :lg="15">
        <div class="right-panel">
          <h2 class="section-title">可选模型</h2>
          <div class="optional-toolbar">
            <a-input-search
              v-model:value="optionalSearch"
              placeholder="搜索"
              allow-clear
              class="optional-search"
              @search="loadOptionalModels"
            />
            <div class="filter-tags">
              <a-tag
                v-for="tag in capabilityTags"
                :key="tag.value"
                :color="optionalCapability === tag.value ? 'blue' : 'default'"
                class="filter-tag"
                @click="toggleCapability(tag.value)"
              >
                {{ tag.label }}
              </a-tag>
            </div>
          </div>
          <div v-if="optionalModels.length" class="optional-list optional-list-rows">
            <div
              v-for="m in optionalModels"
              :key="m.provider + '|' + m.model"
              class="optional-row"
              @click="onAddOptionalModel(m)"
            >
              <span class="optional-row-icon">{{ m.icon || "🤖" }}</span>
              <span class="optional-row-name">{{ m.providerLabel }} - {{ m.modelLabel }}</span>
              <div class="optional-row-tags">
                <a-tag
                  v-for="cap in m.capabilities || []"
                  :key="cap"
                  class="cap-tag cap-tag-clickable"
                  @click.stop="toggleCapability(cap)"
                >
                  {{ cap }}
                </a-tag>
              </div>
              <a-button type="primary" size="small" class="optional-row-add">添加</a-button>
            </div>
          </div>
          <a-spin v-else-if="optionalLoading" style="width: 100%; padding: 24px" />
          <a-empty v-else description="暂无匹配的可选模型" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
        </div>
      </a-col>
    </a-row>

    <!-- 模型参数设置弹窗 -->
    <a-modal
      v-model:open="paramModalVisible"
      title="模型参数设置"
      width="520px"
      :footer="null"
      destroy-on-close
      @cancel="closeParamModal"
    >
      <a-form :model="paramForm" layout="vertical" :label-col="{ span: 24 }">
        <a-form-item label="供应商">
          <a-input :value="paramForm.providerLabel" disabled />
        </a-form-item>
        <a-form-item label="模型">
          <a-input :value="paramForm.modelLabel" disabled />
        </a-form-item>
        <a-form-item label="API Key" v-if="paramFormNeedsApiKey">
          <a-input-password v-model:value="paramForm.api_key" placeholder="请输入 API Key" />
        </a-form-item>
        <a-form-item label="API Base URL" v-if="paramFormNeedsApiBase">
          <a-input v-model:value="paramForm.api_base" placeholder="自定义 API 地址（可选）" />
        </a-form-item>
        <a-form-item label="Temperature">
          <a-slider v-model:value="paramForm.temperature" :min="0" :max="2" :step="0.1" />
        </a-form-item>
        <a-form-item label="Max Tokens">
          <a-input-number v-model:value="paramForm.max_tokens" :min="256" :max="32000" style="width: 100%" />
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" @click="saveParamConfig" :loading="savingParam"> <SaveOutlined /> 保存 </a-button>
            <a-button @click="saveAndSetCurrent" :loading="savingParam"> 保存并设为当前 </a-button>
            <a-button @click="testParamConnection" :loading="testingParam"> <ThunderboltOutlined /> 测试连接 </a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 模型添加弹窗（从可选模型点击添加时，或手动选择供应商+模型） -->
    <a-modal
      v-model:open="addModalVisible"
      title="添加模型"
      width="520px"
      :footer="null"
      destroy-on-close
      @cancel="closeAddModal"
    >
      <a-form :model="addForm" layout="vertical" :label-col="{ span: 24 }">
        <a-form-item label="供应商" name="provider" :rules="[{ required: true, message: '请选择供应商' }]">
          <a-select v-model:value="addForm.provider" placeholder="请选择供应商" @change="onAddProviderChange">
            <a-select-option v-for="p in addProviders" :key="p.value" :value="p.value">{{ p.label }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="模型" name="model" :rules="[{ required: true, message: '请选择模型' }]">
          <a-select v-model:value="addForm.model" placeholder="请选择模型">
            <a-select-option v-for="m in addModelOptions" :key="m.value" :value="m.value">{{ m.label }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="API Key" v-if="addFormNeedsApiKey">
          <a-input-password v-model:value="addForm.api_key" placeholder="请输入 API Key" />
        </a-form-item>
        <a-form-item label="API Base URL" v-if="addFormNeedsApiBase">
          <a-input v-model:value="addForm.api_base" placeholder="自定义 API 地址（可选）" />
        </a-form-item>
        <a-form-item label="Temperature">
          <a-slider v-model:value="addForm.temperature" :min="0" :max="2" :step="0.1" />
        </a-form-item>
        <a-form-item label="Max Tokens">
          <a-input-number v-model:value="addForm.max_tokens" :min="256" :max="32000" style="width: 100%" />
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" @click="saveAddModel" :loading="savingAdd"> <SaveOutlined /> 保存 </a-button>
            <a-button @click="saveAddAndSetCurrent" :loading="savingAdd"> 保存并设为当前 </a-button>
            <a-button @click="closeAddModal"> 取消 </a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { message, Modal, Empty } from "ant-design-vue";
import {
  QuestionCircleOutlined,
  SettingOutlined,
  DeleteOutlined,
  SaveOutlined,
  ThunderboltOutlined
} from "@ant-design/icons-vue";
import {
  getDefaultModels,
  updateDefaultModels,
  getDefaultModelOptions,
  getAddedProviders,
  getOptionalModels,
  getModelConfig,
  updateLLMConfig,
  deleteModelConfig,
  testLLMConnection
} from "@/api/modules/llmConfig";

// 默认模型表单
const defaultForm = ref({
  llm: undefined,
  embedding: undefined,
  vlm: undefined,
  asr: undefined,
  rerank: undefined,
  tts: undefined
});
const defaultOptions = ref({
  llm: [],
  embedding: [],
  vlm: [],
  asr: [],
  rerank: [],
  tts: []
});

function filterOption(input, option) {
  const label = option?.label ?? "";
  return String(label)
    .toLowerCase()
    .includes((input || "").toLowerCase());
}

async function loadDefaultModels() {
  try {
    const data = await getDefaultModels();
    if (data && typeof data === "object") {
      defaultForm.value = {
        llm: data.llm || undefined,
        embedding: data.embedding || undefined,
        vlm: data.vlm || undefined,
        asr: data.asr || undefined,
        rerank: data.rerank || undefined,
        tts: data.tts || undefined
      };
    }
  } catch (e) {
    console.error("加载默认模型失败:", e);
  }
}

async function loadDefaultOptions() {
  try {
    const data = await getDefaultModelOptions();
    defaultOptions.value = {
      llm: data.llm || [],
      embedding: data.embedding || [],
      vlm: data.vlm || [],
      asr: data.asr || [],
      rerank: data.rerank || [],
      tts: data.tts || []
    };
  } catch (e) {
    console.error("加载默认模型选项失败:", e);
  }
}

function onDefaultModelChange(field, value) {
  updateDefaultModels({ [field]: value || "" }).catch(e => {
    message.error("保存默认模型失败: " + (e.response?.data?.detail || e.message));
  });
}

// 已添加的模型（按供应商分组，前端展平为每模型一行）
const addedProviders = ref([]);

const addedModelList = computed(() => {
  const list = [];
  for (const item of addedProviders.value) {
    for (const m of item.models || []) {
      list.push({
        provider: item.provider,
        providerLabel: item.providerLabel,
        model: m.model,
        modelLabel: m.modelLabel,
        icon: item.icon
      });
    }
  }
  return list;
});

// 假数据（无真实配置时展示，便于调试 UI）
const FAKE_ADDED_PROVIDERS = [
  {
    provider: "openai",
    providerLabel: "OpenAI",
    icon: "🤖",
    models: [
      { model: "gpt-4o", modelLabel: "GPT-4o" },
      { model: "gpt-4o-mini", modelLabel: "GPT-4o Mini" }
    ]
  },
  {
    provider: "ollama",
    providerLabel: "Ollama (本地)",
    icon: "🦙",
    models: [{ model: "llama3.2", modelLabel: "Llama 3.2" }]
  },
  {
    provider: "zhipu",
    providerLabel: "智谱 AI",
    icon: "🇨🇳",
    models: [{ model: "glm-4-plus", modelLabel: "GLM-4 Plus" }]
  }
];

async function loadAddedProviders() {
  try {
    const data = await getAddedProviders();
    const list = Array.isArray(data) ? data : [];
    // 无数据时使用假数据展示
    addedProviders.value = list.length > 0 ? list : FAKE_ADDED_PROVIDERS;
  } catch (e) {
    console.error("加载已添加模型失败:", e);
    addedProviders.value = FAKE_ADDED_PROVIDERS;
  }
}

const providerLabels = {
  openai: "OpenAI",
  azure_openai: "Azure OpenAI",
  anthropic: "Anthropic Claude",
  ollama: "Ollama (本地)",
  zhipu: "智谱 AI",
  qwen: "通义千问",
  mock: "Mock (测试)"
};

function onDeleteModel(row) {
  Modal.confirm({
    title: "确认删除",
    content: `确定要删除「${row.providerLabel} - ${row.modelLabel}」的配置吗？`,
    okText: "删除",
    okType: "danger",
    cancelText: "取消",
    onOk: async () => {
      try {
        await deleteModelConfig(row.provider, row.model);
        message.success("已删除");
        loadAddedProviders();
      } catch (e) {
        message.error("删除失败: " + (e.response?.data?.detail || e.message));
      }
    }
  });
}

// 可选模型（右侧，一行一个模型）
const optionalSearch = ref("");
const optionalCapability = ref("All");
const optionalModels = ref([]);
const optionalLoading = ref(false);

const capabilityTags = [
  { value: "All", label: "All" },
  { value: "IMAGE2TEXT", label: "IMAGE2TEXT" },
  { value: "LLM", label: "LLM" },
  { value: "MODERATION", label: "MODERATION" },
  { value: "SPEECH2TEXT", label: "SPEECH2TEXT" },
  { value: "TEXT EMBEDDING", label: "TEXT EMBEDDING" },
  { value: "TEXT RE-RANK", label: "TEXT RE-RANK" },
  { value: "TTS", label: "TTS" }
];

function toggleCapability(value) {
  optionalCapability.value = value;
  // 显式传入 capability，确保点击 Tag 后立即用该值请求
  loadOptionalModels(value);
}

async function loadOptionalModels(capabilityOverride) {
  optionalLoading.value = true;
  try {
    const params = {};
    if (optionalSearch.value) params.search = optionalSearch.value;
    const cap = capabilityOverride !== undefined ? capabilityOverride : optionalCapability.value;
    if (cap && cap !== "All") params.capability = cap;
    const data = await getOptionalModels(params);
    optionalModels.value = Array.isArray(data) ? data : [];
  } catch (e) {
    console.error("加载可选模型失败:", e);
    optionalModels.value = [];
  } finally {
    optionalLoading.value = false;
  }
}

const addProviders = [
  { value: "openai", label: "OpenAI" },
  { value: "azure_openai", label: "Azure OpenAI" },
  { value: "anthropic", label: "Anthropic Claude" },
  { value: "ollama", label: "Ollama (本地)" },
  { value: "zhipu", label: "智谱 AI" },
  { value: "qwen", label: "通义千问" },
  { value: "mock", label: "Mock (测试)" }
];

const supportedProviderIds = ["openai", "azure_openai", "anthropic", "ollama", "zhipu", "qwen", "mock"];

function onAddOptionalModel(m) {
  addForm.value.provider = supportedProviderIds.includes(m.provider) ? m.provider : "";
  addForm.value.model = m.model || "";
  addModalVisible.value = true;
  if (addForm.value.provider) {
    onAddProviderChange();
  }
}

// 参数弹窗
const paramModalVisible = ref(false);
const paramForm = ref({
  provider: "",
  model: "",
  providerLabel: "",
  modelLabel: "",
  api_key: "",
  api_base: "",
  temperature: 0.7,
  max_tokens: 2048
});
const savingParam = ref(false);
const testingParam = ref(false);
const needApiKeyProviders = ["openai", "azure_openai", "anthropic", "zhipu", "qwen"];
const needApiBaseProviders = ["ollama", "azure_openai"];
const paramFormNeedsApiKey = computed(() => needApiKeyProviders.includes(paramForm.value.provider));
const paramFormNeedsApiBase = computed(() => needApiBaseProviders.includes(paramForm.value.provider));

function openParamModal(provider, model, modelLabel) {
  paramForm.value = {
    provider,
    model,
    providerLabel: providerLabels[provider] || provider,
    modelLabel: modelLabel || model,
    api_key: "",
    api_base: "",
    temperature: 0.7,
    max_tokens: 2048
  };
  paramModalVisible.value = true;
  if (provider && model) loadParamConfig(provider, model);
}

async function loadParamConfig(provider, model) {
  try {
    const data = await getModelConfig(provider, model);
    paramForm.value = {
      ...paramForm.value,
      api_key: data.api_key ?? "",
      api_base: data.api_base ?? "",
      temperature: data.temperature ?? 0.7,
      max_tokens: data.max_tokens ?? 2048
    };
  } catch (e) {
    console.error("加载模型配置失败:", e);
  }
}

function closeParamModal() {
  paramModalVisible.value = false;
}

async function saveParamConfig() {
  savingParam.value = true;
  try {
    await updateLLMConfig({ ...paramForm.value, set_as_current: false });
    message.success("参数已保存");
    closeParamModal();
    loadAddedProviders();
  } catch (e) {
    message.error("保存失败: " + (e.response?.data?.detail || e.message));
  } finally {
    savingParam.value = false;
  }
}

async function saveAndSetCurrent() {
  savingParam.value = true;
  try {
    await updateLLMConfig({ ...paramForm.value, set_as_current: true });
    message.success("已保存并设为当前模型");
    closeParamModal();
    loadAddedProviders();
  } catch (e) {
    message.error("保存失败: " + (e.response?.data?.detail || e.message));
  } finally {
    savingParam.value = false;
  }
}

async function testParamConnection() {
  testingParam.value = true;
  try {
    const res = await testLLMConnection({
      provider: paramForm.value.provider,
      model: paramForm.value.model,
      api_key: paramForm.value.api_key || undefined,
      api_base: paramForm.value.api_base || undefined
    });
    if (res && res.success) {
      message.success("连接成功: " + (res.message || "").slice(0, 50));
    } else {
      message.error("连接失败: " + (res?.message || "未知错误"));
    }
  } catch (e) {
    message.error("测试失败: " + (e.response?.data?.detail || e.message));
  } finally {
    testingParam.value = false;
  }
}

// 添加弹窗
const addModalVisible = ref(false);
const addForm = ref({
  provider: "",
  model: "",
  api_key: "",
  api_base: "",
  temperature: 0.7,
  max_tokens: 2048
});
const savingAdd = ref(false);
const addModelsByProvider = {
  openai: [
    { value: "gpt-4o", label: "GPT-4o" },
    { value: "gpt-4o-mini", label: "GPT-4o Mini" },
    { value: "gpt-4-turbo", label: "GPT-4 Turbo" },
    { value: "gpt-3.5-turbo", label: "GPT-3.5 Turbo" }
  ],
  azure_openai: [
    { value: "gpt-4o", label: "GPT-4o" },
    { value: "gpt-4", label: "GPT-4" },
    { value: "gpt-35-turbo", label: "GPT-3.5 Turbo" }
  ],
  anthropic: [
    { value: "claude-3-5-sonnet-20241022", label: "Claude 3.5 Sonnet" },
    { value: "claude-3-opus-20240229", label: "Claude 3 Opus" },
    { value: "claude-3-haiku-20240307", label: "Claude 3 Haiku" }
  ],
  ollama: [
    { value: "llama3.2", label: "Llama 3.2" },
    { value: "qwen2.5", label: "Qwen 2.5" },
    { value: "mistral", label: "Mistral" },
    { value: "deepseek-r1", label: "DeepSeek R1" }
  ],
  zhipu: [
    { value: "glm-4-plus", label: "GLM-4 Plus" },
    { value: "glm-4", label: "GLM-4" },
    { value: "glm-4-flash", label: "GLM-4 Flash" }
  ],
  qwen: [
    { value: "qwen-max", label: "Qwen Max" },
    { value: "qwen-plus", label: "Qwen Plus" },
    { value: "qwen-turbo", label: "Qwen Turbo" }
  ],
  mock: [{ value: "mock", label: "Mock Model" }]
};
const addModelOptions = computed(() => addModelsByProvider[addForm.value.provider] || []);
const addFormNeedsApiKey = computed(() => needApiKeyProviders.includes(addForm.value.provider));
const addFormNeedsApiBase = computed(() => needApiBaseProviders.includes(addForm.value.provider));

function closeAddModal() {
  addModalVisible.value = false;
}

function onAddProviderChange() {
  addForm.value.model = "";
}

async function saveAddModel() {
  if (!addForm.value.provider || !addForm.value.model) {
    message.warning("请选择供应商和模型");
    return;
  }
  savingAdd.value = true;
  try {
    await updateLLMConfig({
      provider: addForm.value.provider,
      model: addForm.value.model,
      api_key: addForm.value.api_key || undefined,
      api_base: addForm.value.api_base || undefined,
      temperature: addForm.value.temperature,
      max_tokens: addForm.value.max_tokens,
      set_as_current: false
    });
    message.success("模型已添加");
    closeAddModal();
    loadAddedProviders();
  } catch (e) {
    message.error("添加失败: " + (e.response?.data?.detail || e.message));
  } finally {
    savingAdd.value = false;
  }
}

async function saveAddAndSetCurrent() {
  if (!addForm.value.provider || !addForm.value.model) {
    message.warning("请选择供应商和模型");
    return;
  }
  savingAdd.value = true;
  try {
    await updateLLMConfig({
      provider: addForm.value.provider,
      model: addForm.value.model,
      api_key: addForm.value.api_key || undefined,
      api_base: addForm.value.api_base || undefined,
      temperature: addForm.value.temperature,
      max_tokens: addForm.value.max_tokens,
      set_as_current: true
    });
    message.success("模型已添加并设为当前");
    closeAddModal();
    loadAddedProviders();
  } catch (e) {
    message.error("添加失败: " + (e.response?.data?.detail || e.message));
  } finally {
    savingAdd.value = false;
  }
}

onMounted(async () => {
  await loadDefaultOptions();
  await loadDefaultModels();
  await loadAddedProviders();
  await loadOptionalModels();
});

watch(optionalSearch, () => {
  loadOptionalModels();
});
</script>

<style scoped lang="scss">
.llm-config-page {
  height: 100%;
  overflow: hidden;

  :deep(.ant-col) {
    height: 100%;
    overflow: hidden;
  }
}

.config-layout {
  height: 100%;
  min-height: 400px;
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
  height: 100%;
  min-height: 0;
}

.left-panel .section.default-models {
  flex-shrink: 0;
}

.section-title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: #262626;
}

.section-desc {
  margin: 0 0 16px;
  font-size: 13px;
  color: #8c8c8c;
}

.subsection-title {
  margin: 0 0 12px;
  font-weight: 600;
  color: #262626;
}

.default-form {
  .required-star {
    margin-right: 2px;
    color: #ff4d4f;
  }

  .label-tip {
    margin-left: 6px;
    font-size: 12px;
    color: #8c8c8c;
  }
}

.added-models {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.added-models .subsection-title {
  flex-shrink: 0;
  margin-bottom: 12px;
}

.added-list-wrap {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.added-models .added-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.added-card {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px 16px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-bottom: none;
  transition: background 0.2s;

  &:last-child {
    border-bottom: 1px solid #f0f0f0;
  }

  &:hover {
    background: #f0f0f0;
  }
}

.added-icon {
  flex-shrink: 0;
  font-size: 20px;
  line-height: 1;
}

.added-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  font-weight: 500;
  color: #262626;
  white-space: nowrap;
}

.added-card-actions {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
  align-items: center;
}

.btn-config {
  font-size: 12px;
}

.btn-delete {
  font-size: 12px;
}

.right-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
  padding: 20px;
  overflow: hidden;
  background: #fafafa;
  border-radius: 8px;
}

.right-panel .section-title {
  flex-shrink: 0;
  margin-bottom: 16px;
}

.optional-toolbar {
  display: flex;
  flex-shrink: 0;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.optional-search {
  max-width: 280px;
}

.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-tag {
  cursor: pointer;
  user-select: none;
}

.optional-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}

.optional-list-rows {
  display: flex;
  flex: 1;
  flex-direction: column;
  grid-template-columns: unset;
  gap: 0;
  min-height: 0;
  overflow-y: auto;
}

.optional-row {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  background: #ffffff;
  border: 1px solid #f0f0f0;
  border-bottom: none;
  transition: background 0.2s;

  &:last-child {
    border-bottom: 1px solid #f0f0f0;
  }

  &:hover {
    background: #f5f9ff;
  }
}

.optional-row-icon {
  flex-shrink: 0;
  font-size: 22px;
  line-height: 1;
}

.optional-row-name {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  font-weight: 500;
  color: #262626;
}

.optional-row-tags {
  display: flex;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 4px;
  min-height: 24px;
}

.cap-tag {
  font-size: 11px;
  line-height: 18px;
}

.cap-tag-clickable {
  cursor: pointer;
}

.cap-tag-clickable:hover {
  opacity: 0.85;
}

.optional-row-add {
  flex-shrink: 0;
}

:deep(.ant-form-item-label > label) {
  font-weight: 500;
}
</style>
