/**
 * 对话配置常量（search_options、generate_options）
 * 供 chat/detail 与 chat/list 共用，保证两边数据一致
 */

export const defaultSearchOptions = {
  top_k: 20,
  threshold: 0,
  search_method: "dense_filter"
};

export const defaultGenerateOptions = {
  model: "Qwen3-30B-A3B-Instrunct-2507",
  temperature: 0.75,
  top_p: 0.95
};

export const searchMethodOptions = [
  { value: "dense", label: "dense（仅向量）" },
  { value: "dense_filter", label: "dense_filter（向量+过滤）" },
  { value: "hybrid", label: "hybrid（混合）" },
  { value: "sparse", label: "sparse（稀疏）" }
];
