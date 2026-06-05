import { message as AntMessage } from "ant-design-vue";

/**
 * @description 根据状态码提示
 * @param status 状态
 */
export const checkResStatus = status => {
  switch (status) {
    case 400:
      AntMessage.error("请求失败！请您稍后重试");
      break;
    case 401:
      AntMessage.error("登录失效！请您重新登录");
      break;
    case 403:
      AntMessage.error("当前账号无权限访问！");
      break;
    case 404:
      AntMessage.error("你所访问的资源不存在！");
      break;
    case 405:
      AntMessage.error("请求方式错误！请您稍后重试");
      break;
    case 408:
      AntMessage.error("请求超时！请您稍后重试");
      break;
    case 500:
      AntMessage.error("服务异常！");
      break;
    case 502:
      AntMessage.error("网关错误！");
      break;
    case 503:
      AntMessage.error("服务不可用！");
      break;
    case 504:
      AntMessage.error("网关超时！");
      break;
    default:
      AntMessage.error("请求失败！");
  }
};
