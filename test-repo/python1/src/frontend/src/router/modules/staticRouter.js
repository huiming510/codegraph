// 静态路由
// 登陆页 首页
export const staticRouters = [
  {
    path: "/",
    redirect: "/home"
  },
  {
    path: "/login",
    name: "login",
    component: () => import("@/views/login/index.vue"),
    meta: { title: "登录" }
  },
  {
    path: "/layout",
    name: "layout",
    component: () => import("@/layouts/index.vue"),
    redirect: "/home",
    children: []
  }
  // {
  //   path: "/",
  //   redirect: "/query"
  // },
  // {
  //   path: "/query",
  //   name: "Query",
  //   component: QueryView
  // },
  // {
  //   path: "/upload",
  //   name: "Upload",
  //   component: UploadView
  // },
  // {
  //   path: "/chat",
  //   name: "Chat",
  //   component: ChatView
  // },
  // {
  //   path: "/logs",
  //   name: "Logs",
  //   component: LogsView
  // }
];

// 错误页
export const errorRouters = [
  {
    path: "/403",
    name: "403",
    component: () => import("@/components/ErrorPages/403.vue"),
    meta: { title: "403" }
  },
  {
    path: "/404",
    name: "404",
    component: () => import("@/components/ErrorPages/404.vue"),
    meta: { title: "404" }
  },
  {
    path: "/500",
    name: "500",
    component: () => import("@/components/ErrorPages/500.vue"),
    meta: { title: "500" }
  },
  {
    path: "/:pathMatch(.*)*",
    component: () => import("@/components/ErrorPages/404.vue")
  }
];
