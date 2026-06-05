import axios from "axios";
import router from "@/router";
import { RequestStates } from "@/config/request";
import { checkResStatus } from "@/api/helper/checkResStatus";
import { useUserStore } from "@/stores/modules/user";
import { LOGIN_URL } from "@/constants/router";
import { showFullScreenLoading, tryHideFullScreenLoading } from "@/components/Loading/fullScreen";
import { message as AntMessage } from "ant-design-vue";

// 配置 config 对象
// https://www.axios-http.cn/docs/req_config
const config = {
  baseURL: import.meta.env.VITE_APP_API_BASE_URL, // 接口基准路径
  timeout: RequestStates.TIMEOUT,
  withCredentials: true // 跨域时允许带凭证
};

// 封装 axios 请求类
class Request {
  // 创建 axios 实例
  service;

  constructor(config) {
    // 实例化 axios
    this.service = axios.create(config);

    /**
     * @description 请求拦截器
     * 客户端发送请求 -> [请求拦截器] -> 服务器
     * token校验(JWT) : 接受服务器返回的 token,存储到 vuex/pinia/本地储存当中
     */
    this.service.interceptors.request.use(
      config => {
        const userStore = useUserStore();
        // 当前请求不需要显示 loading，在 api 服务中通过指定的第三个参数: { loading: true } 来控制，默认不显示
        config.loading ??= false;
        config.loading && showFullScreenLoading();
        // 添加token到header
        if (userStore.token) {
          config.headers["Authorization"] = `Bearer ${userStore.token}`;
        }
        return config;
      },
      error => {
        return Promise.reject(error);
      }
    );

    /**
     * @description 响应拦截器
     *  服务器换返回信息 -> [拦截统一处理] -> 客户端JS获取到信息
     */
    this.service.interceptors.response.use(
      response => {
        const { data, config } = response;
        config.loading && tryHideFullScreenLoading();
        // 统一格式 { code, data, msg }：成功时返回 data，业务失败时按错误处理
        if (data && typeof data.code !== "undefined") {
          if (data.code === 0 || data.code === 200) {
            return data.data;
          }
          AntMessage.error(data.msg || "请求失败");
          return Promise.reject(new Error(data.msg || "请求失败"));
        }
        // 兼容非统一格式（如 blob、流式等）
        return data;
      },
      error => {
        const { response, config } = error;
        config?.loading && tryHideFullScreenLoading();

        // 401 未授权 - 跳转登录（排除登录接口本身）
        if (response?.status === 401 && !config?.url?.includes("/auth/login")) {
          const userStore = useUserStore();
          userStore.logout();
          router.replace(LOGIN_URL);
          AntMessage.error("登录已过期，请重新登录");
          return Promise.reject(error);
        }

        // 请求超时 && 网络错误
        if (error.message.indexOf("timeout") !== -1) AntMessage.error("请求超时！请您稍后重试");
        if (error.message.indexOf("Network Error") !== -1) AntMessage.error("网络错误！请您稍后重试");

        // 统一格式错误体 { code, data, msg }
        if (response?.data?.msg) {
          AntMessage.error(response.data.msg);
        } else if (response) {
          checkResStatus(response.status);
        }

        // 服务器结果都没有返回
        if (!window.navigator.onLine) router.replace("/500");
        return Promise.reject(error);
      }
    );
  }

  /**
   * @description 常用请求方法封装
   */
  get(url, params, _object = {}) {
    return this.service.get(url, { params, ..._object });
  }
  post(url, params, _object = {}) {
    return this.service.post(url, params, _object);
  }
  put(url, params, _object = {}) {
    return this.service.put(url, params, _object);
  }
  delete(url, params, _object = {}) {
    return this.service.delete(url, { params, ..._object });
  }
  download(url, params, _object = {}) {
    return this.service.post(url, params, { ..._object, responseType: "blob" });
  }
}

export default new Request(config);
