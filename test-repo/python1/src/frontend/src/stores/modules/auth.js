import { defineStore } from "pinia";
import { getFlatMenuList } from "@/utils/routerUtils";
import { getMenuList as getMenuListApi } from "@/api/modules/login";

// 权限状态：菜单/路由由后台 auth/menu 统一返回，admin 拥有全部，普通用户无 system
export const useAuthStore = defineStore("AuthState", {
  state: () => ({
    authMenuList: []
  }),
  getters: {
    // 返回的初始菜单
    authMenuListGet: state => state.authMenuList,
    // 扁平化菜单，做路由使用
    flatMenuListGet: state => getFlatMenuList(state.authMenuList)
  },
  actions: {
    async getMenuList() {
      try {
        const list = await getMenuListApi();
        this.authMenuList = Array.isArray(list) ? list : [];
      } catch {
        this.authMenuList = [];
      }
    },
    /** 登出或进入登录页时清空菜单，避免换账号后仍用旧菜单/路由 */
    clearMenuList() {
      this.authMenuList = [];
    }
  }
});
