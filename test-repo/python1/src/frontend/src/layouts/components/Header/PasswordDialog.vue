<!--
  头部「修改密码」弹窗：当前用户修改自己的登录密码，调用 PUT /api/auth/password。
-->
<template>
  <a-modal
    v-model:open="dialogVisible"
    title="修改密码"
    :width="500"
    :maskClosable="false"
    :destroyOnClose="true"
    @cancel="handleCancel"
  >
    <a-form
      ref="formRef"
      :model="form"
      :rules="rules"
      layout="vertical"
      autocomplete="off"
    >
      <a-form-item label="原密码" name="old_password">
        <a-input-password
          v-model:value="form.old_password"
          placeholder="请输入原密码"
          allow-clear
        />
      </a-form-item>
      <a-form-item label="新密码" name="new_password">
        <a-input-password
          v-model:value="form.new_password"
          placeholder="请输入新密码（至少 6 位）"
          allow-clear
        />
      </a-form-item>
      <a-form-item label="确认新密码" name="confirm_password">
        <a-input-password
          v-model:value="form.confirm_password"
          placeholder="请再次输入新密码"
          allow-clear
        />
      </a-form-item>
    </a-form>
    <template #footer>
      <a-button @click="handleCancel">取消</a-button>
      <a-button type="primary" :loading="loading" @click="handleSubmit">
        确认
      </a-button>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { message } from "ant-design-vue";
import { changePassword } from "@/api/modules/login";

const dialogVisible = ref(false);
const formRef = ref();
const loading = ref(false);

const form = reactive({
  old_password: "",
  new_password: "",
  confirm_password: ""
});

/** 校验：确认新密码必须与新密码一致 */
const validateConfirm = (_rule: unknown, value: string) => {
  if (value && value !== form.new_password) {
    return Promise.reject("两次输入的新密码不一致");
  }
  return Promise.resolve();
};

const rules = {
  old_password: [{ required: true, message: "请输入原密码", trigger: "blur" }],
  new_password: [
    { required: true, message: "请输入新密码", trigger: "blur" },
    { min: 6, message: "新密码至少 6 位", trigger: "blur" }
  ],
  confirm_password: [
    { required: true, message: "请再次输入新密码", trigger: "blur" },
    { validator: validateConfirm, trigger: "blur" }
  ]
};

/** 重置表单并关闭弹窗 */
function resetAndClose() {
  form.old_password = "";
  form.new_password = "";
  form.confirm_password = "";
  formRef.value?.resetFields();
  dialogVisible.value = false;
}

function handleCancel() {
  resetAndClose();
}

/** 提交修改密码：校验通过后调用 PUT /api/auth/password */
async function handleSubmit() {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }
  loading.value = true;
  try {
    await changePassword({
      old_password: form.old_password,
      new_password: form.new_password
    });
    message.success("密码修改成功，请使用新密码重新登录");
    resetAndClose();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    message.error(err.response?.data?.detail || "修改密码失败");
  } finally {
    loading.value = false;
  }
}

/** 打开弹窗（由 Header 头像下拉菜单调用） */
function openDialog() {
  dialogVisible.value = true;
}

defineExpose({ openDialog });
</script>
