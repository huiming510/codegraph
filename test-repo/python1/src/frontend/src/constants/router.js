// 路由白名单
export const ROUTER_WHITE_LIST = ["/500"];

// 登录路由
export const LOGIN_URL = "/login";

// 首页路由
export const HOEM_URL = "/home";

export const MOCK_MENU_LIST_PROMISE = {
  code: 200,
  data: [
    {
      path: "/home",
      name: "home",
      component: "/home/index",
      meta: {
        icon: "",
        title: "首页",
        isHide: true,
        isLink: false,
        isFull: false,
        closable: false
      }
    },
    {
      path: "/knowledge",
      name: "knowledge",
      component: "/knowledge/index",
      meta: {
        icon: "",
        title: "知识库",
        isHide: false,
        isLink: false,
        isFull: false,
        closable: false
      },
      children: [
        {
          path: "/knowledge/detail/:id",
          name: "knowledgeDetail",
          component: "/knowledge/detail/index",
          meta: {
            icon: "Menu",
            title: "知识库详情",
            isHide: true,
            isLink: false,
            isFull: false,
            closable: false
          }
        },
        {
          path: "/knowledge/upload/",
          name: "knowledgeDetail",
          component: "/knowledge/upload/index",
          meta: {
            icon: "Menu",
            title: "文档上传",
            isHide: true,
            isLink: false,
            isFull: false,
            closable: false
          }
        }
      ]
    },
    {
      path: "/queryRag",
      name: "queryRag",
      component: "/queryRag/index",
      meta: {
        icon: "",
        title: "Search",
        isHide: false,
        isLink: false,
        isFull: false,
        closable: false
      }
    },
    {
      path: "/chat",
      name: "chat",
      component: "/chat/index",
      meta: {
        icon: "",
        title: "Chat",
        isHide: false,
        isLink: false,
        isFull: false,
        closable: false
      }
    },
    {
      path: "/agent",
      name: "agent",
      component: "/agent/index",
      meta: {
        icon: "",
        title: "Agent",
        isHide: false,
        isLink: false,
        isFull: false,
        closable: false
      },
      children: [
        {
          path: "/agent/flow/:id",
          name: "flow",
          component: "/agent/flow/index",
          meta: {
            icon: "Menu",
            title: "Agent编排",
            isHide: true,
            isLink: false,
            isFull: true,
            closable: false
          }
        }
      ]
    },
    {
      path: "/system",
      name: "system",
      component: "/system/index",
      redirect: "/system/companyMgt",
      meta: {
        icon: "",
        title: "系统设置",
        isHide: false,
        isLink: false,
        isFull: false,
        closable: false
      },
      children: [
        {
          path: "/system/models",
          name: "models",
          component: "/system/models/index",
          meta: {
            icon: "icon-companyMgt",
            title: "模型设置",
            isHide: false,
            isLink: false,
            isFull: false,
            closable: false
          }
        },
        {
          path: "/system/logs",
          name: "logs",
          component: "/system/logs/index",
          meta: {
            icon: "icon-companyMgt",
            title: "日志管理",
            isHide: false,
            isLink: false,
            isFull: false,
            closable: false
          }
        },
        {
          path: "/system/esConfig",
          name: "esConfig",
          component: "/system/esConfig/index",
          meta: {
            icon: "icon-companyMgt",
            title: "ES环境配置",
            isHide: false,
            isLink: false,
            isFull: false,
            closable: false
          }
        },
        {
          path: "/system/companyMgt",
          name: "companyMgt",
          component: "/system/companyMgt/index",
          meta: {
            icon: "icon-companyMgt",
            title: "公司管理",
            isHide: false,
            isLink: false,
            isFull: false,
            closable: false
          }
        },
        {
          path: "/system/deptMgt",
          name: "deptMgt",
          component: "/system/deptMgt/index",
          meta: {
            icon: "icon-deptMgt",
            title: "部门管理",
            isHide: false,
            isLink: false,
            isFull: false,
            closable: false
          }
        },
        {
          path: "/system/roleMgt",
          name: "roleMgt",
          component: "/system/roleMgt/index",
          meta: {
            icon: "icon-roleMgt",
            title: "角色管理",
            isHide: false,
            isLink: false,
            isFull: false,
            closable: false
          }
        },
        {
          path: "/system/accountMgt",
          name: "accountMgt",
          component: "/system/accountMgt/index",
          meta: {
            icon: "icon-accountMgt",
            title: "用户管理",
            isHide: false,
            isLink: false,
            isFull: false,
            closable: false
          }
        },
        {
          path: "/system/menuMgt",
          name: "menuMange",
          component: "/system/menuMgt/index",
          meta: {
            icon: "icon-menuMgt",
            title: "菜单管理",
            isHide: false,
            isLink: false,
            isFull: false,
            closable: false
          }
        },
        {
          path: "/system/dataDict",
          name: "dataDict",
          component: "/system/dataDict/index",
          meta: {
            icon: "icon-dataDict",
            title: "数据字典",
            isHide: false,
            isLink: false,
            isFull: false,
            closable: false
          }
        },
        {
          path: "/system/timingTask",
          name: "timingTask",
          component: "/system/timingTask/index",
          meta: {
            icon: "icon-timingTask",
            title: "定时任务",
            isHide: false,
            isLink: false,
            isFull: false,
            closable: false
          }
        },
        {
          path: "/system/systemLog",
          name: "systemLog",
          component: "/system/systemLog/index",
          meta: {
            icon: "icon-systemLog",
            title: "系统日志",
            isHide: false,
            isLink: false,
            isFull: false,
            closable: false
          }
        }
      ]
    }
  ],
  msg: "成功"
};
