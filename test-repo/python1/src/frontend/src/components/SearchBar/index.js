import { h, render } from "vue";
import search from "./index.vue";

class SearchBarCreator {
  container;

  constructor() {
    this.container = document.createElement("div");
    this.container.setAttribute("id", "search-bar-container");
  }

  open() {
    if (!document.body.contains(this.container)) {
      console.log("Opening search bar...");
      let vnode = h(search);
      render(vnode, this.container);
      document.body.appendChild(this.container);
      // 触发 openSearch 事件，让 Vue 组件绑定事件
      document.dispatchEvent(new Event("openSearch"));
    }
  }

  close() {
    if (this.container && document.body.contains(this.container)) {
      console.log("Closing search bar...");
      document.body.removeChild(this.container);
      // 触发 closeSearch 事件，让 Vue 组件解绑事件
      document.dispatchEvent(new Event("closeSearch"));
    }
  }
}

const searchBar = new SearchBarCreator();

export default searchBar;
