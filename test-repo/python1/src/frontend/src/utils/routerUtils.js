/**
 * @description 菜单按照group字段进行分组
 * @param {Array} menuList
 * @return Array
 */
export const getGroupMenuList = menuList => {
  const groupMap = new Map();
  console.log(menuList);

  menuList.forEach(route => {
    if (route.meta?.isHide) return;
    const groupId = route.meta?.group ?? "未分组";
    const groupTitle = route.meta?.groupTitle ?? "未分组";
    if (!groupMap.has(groupId)) {
      groupMap.set(groupId, {
        id: groupId,
        title: groupTitle,
        item: []
      });
    }
    groupMap.get(groupId).item.push(route);
  });

  // 转为数组，并过滤掉空组
  return Array.from(groupMap.values())
    .filter(group => group.item.length > 0)
    .sort((a, b) => a.id - b.id); // 可选：按 id 排序
};

/**
 * @description 扁平化菜单为动态路由
 * @param {Array} menuList
 * @return Array
 */
export const getFlatMenuList = menuList => {
  let newMenuList = JSON.parse(JSON.stringify(menuList));
  return newMenuList.flatMap(item => [item, ...(item.children ? getFlatMenuList(item.children) : [])]);
};
