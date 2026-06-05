import router from "@/router";
import { isType } from "@/utils";
import { useUserStore } from "@/stores/modules/user";
import { useAuthStore } from "@/stores/modules/auth";
import { LOGIN_URL } from "@/constants/router";
import { notification } from "ant-design-vue";

//  导入views 所有文件
const modules = import.meta.glob("@/views/**/*.vue");

export const initDynamicRouters = async () => {
  const userStore = useUserStore();
  const authStore = useAuthStore();
  try {
    // 先按当前菜单移除已注册的动态路由（换账号登录时避免旧路由残留导致 404），再拉取新菜单
    authStore.flatMenuListGet.forEach(route => {
      const { name } = route;
      if (name && router.hasRoute(name)) router.removeRoute(name);
    });
    await authStore.getMenuList();
    // 判断当前用户有没有菜单权限
    if (!authStore.authMenuListGet.length) {
      notification.warning({
        message: "无权限访问",
        description: "当前账号无任何菜单权限，请联系系统管理员！",
        duration: 3
      });
      userStore.setToken("");
      router.replace(LOGIN_URL);
      return Promise.reject("No permission");
    }
    // 添加动态路由
    // Object.entries(authStore.flatMenuListGet).forEach(([groupInfo]) => {
    //   groupInfo.forEach(item => {
    //     item.children && delete item.children;
    //     if (item.component && isType(item.component) == "string") {
    //       item.component = modules["/src/views" + item.component + ".vue"];
    //     }
    //     if (item.meta.isFull) {
    //       router.addRoute(item);
    //     } else {
    //       router.addRoute("layout", item);
    //     }
    //   });
    // });
    authStore.flatMenuListGet.forEach(item => {
      item.children && delete item.children;
      if (item.component && isType(item.component) == "string") {
        const componentPath = "/src/views" + item.component + ".vue";
        console.log("组件路径:", componentPath);
        item.component = modules[componentPath];
        console.log("组件是否加载:", !!item.component);
      }
      console.log("添加路由:", item.path, item.name, "组件:", !!item.component);
      if (item.meta.isFull) {
        router.addRoute(item);
      } else {
        router.addRoute("layout", item);
      }
    });

    console.log(
      "所有路由:",
      router.getRoutes().map(r => ({ name: r.name, path: r.path }))
    );
  } catch (e) {
    // 当权限请求出错时，重定向到登陆页
    userStore.setToken("");
    router.replace(LOGIN_URL);
    return Promise.reject(e);
  }
};
