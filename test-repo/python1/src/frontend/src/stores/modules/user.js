import { defineStore } from "pinia";
import piniaPersistConfig from "@/stores/helper/persist";

export const useUserStore = defineStore("UserState", {
  state: () => ({
    token: "",
    userInfo: null
  }),
  getters: {
    isLoggedIn: state => !!state.token,
    isAdmin: state => state.userInfo?.role === "admin",
    username: state => state.userInfo?.username || "",
    nickname: state => state.userInfo?.nickname || "用户",
    role: state => state.userInfo?.role || "guest"
  },
  actions: {
    setToken(token) {
      this.token = token;
    },
    setUserInfo(userInfo) {
      this.userInfo = userInfo;
    },
    logout() {
      this.token = "";
      this.userInfo = null;
    }
  },
  persist: piniaPersistConfig("user", ["token", "userInfo"])
});
