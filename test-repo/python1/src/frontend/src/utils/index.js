/**
 * @description 判断简单数据类型
 * @return string
 */
export const isType = val => {
  if (val === null) return "null";
  if (typeof val !== "object") return typeof val;
  else return Object.prototype.toString.call(val).slice(8, -1).toLocaleLowerCase();
};
