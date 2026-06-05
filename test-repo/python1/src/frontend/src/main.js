import { createApp } from "vue";
import App from "./App.vue";

// router
import router from "@/router";
// pinia
import pinia from "@/stores";
// custom directives
import directives from "@/directives/index";
// ant-design-vue
import Antd from "ant-design-vue";
// svg icons
import "virtual:svg-icons-register";
// ant-design-vue css
import "ant-design-vue/dist/reset.css";
// font css
// import "@/assets/fonts/font.scss";
// iconfont css
import "@/assets/iconfont/iconfont.scss";
// element css
// import "@/styles/element.scss";
// common css
import "@/styles/common.scss";
// reset css
import "@/styles/reset.scss";

const app = createApp(App);

app.use(Antd).use(directives).use(router).use(pinia).mount("#app");
