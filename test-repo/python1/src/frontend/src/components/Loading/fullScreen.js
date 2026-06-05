import { message } from "ant-design-vue";

/* 全局请求 loading */
const LOADING_KEY = "global_fullscreen_loading";
let isLoadingShown = false;

/**
 * @description 开启 Loading
 * */
const startLoading = () => {
  if (isLoadingShown) return;
  isLoadingShown = true;
  message.loading({
    content: "加载中...",
    key: LOADING_KEY,
    duration: 0
  });
};

/**
 * @description 结束 Loading
 * */
const endLoading = () => {
  if (!isLoadingShown) return;
  isLoadingShown = false;
  message.destroy(LOADING_KEY);
};

/**
 * @description 显示全屏加载
 * */
let needLoadingRequestCount = 0;
export const showFullScreenLoading = () => {
  if (needLoadingRequestCount === 0) {
    startLoading();
  }
  needLoadingRequestCount++;
};

/**
 * @description 隐藏全屏加载
 * */
export const tryHideFullScreenLoading = () => {
  if (needLoadingRequestCount <= 0) return;
  needLoadingRequestCount--;
  if (needLoadingRequestCount === 0) {
    endLoading();
  }
};
