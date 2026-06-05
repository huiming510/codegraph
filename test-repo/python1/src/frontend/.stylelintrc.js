// @see: https://stylelint.io

module.exports = {
  extends: ["stylelint-config-standard", "stylelint-config-html/vue", "stylelint-config-recess-order"],
  plugins: ["stylelint-scss", "stylelint-order", "stylelint-prettier"],
  overrides: [
    {
      files: ["**/*.(css|html|vue)"],
      customSyntax: "postcss-html"
    },
    {
      files: ["*.scss", "**/*.scss"],
      customSyntax: "postcss-scss",
      extends: ["stylelint-config-standard-scss", "stylelint-config-recommended-vue/scss"]
    }
  ],
  rules: {
    "prettier/prettier": true,
    "function-url-quotes": "always", // URL 的引号 "always(必须加上引号)"|"never(没有引号)"
    "color-hex-length": "long", // 指定 16 进制颜色的简写或扩写 "short(16进制简写)"|"long(16进制扩写)"
    "font-family-no-missing-generic-family-keyword": null, // 禁止在字体族名称列表中缺少通用字体族关键字
    "keyframes-name-pattern": null, // 关闭 keyframes 命名检查
    "property-no-unknown": null, // 禁止未知的属性
    "no-empty-source": null, // 禁止空源码
    "selector-class-pattern": null, // 强制选择器类名的格式
    "value-no-vendor-prefix": null, // 关闭 vendor-prefix (为了解决多行省略 -webkit-box)
    "no-descending-specificity": null, // 不允许较低特异性的选择器出现在覆盖较高特异性的选择器
    "value-keyword-case": null, // 解决在 scss 中使用 v-bind 大写单词报错
    "scss/dollar-variable-pattern": null,
    "selector-pseudo-class-no-unknown": [
      true,
      {
        ignorePseudoClasses: ["deep", "global"]
      }
    ],
    "selector-pseudo-element-no-unknown": [
      true,
      {
        ignorePseudoElements: ["v-deep", "v-global", "v-slotted"]
      }
    ],
    "at-rule-no-unknown": [
      true,
      {
        ignoreAtRules: ["apply", "variants", "responsive", "screen", "function", "if", "each", "include", "mixin", "use"]
      }
    ],
    "rule-empty-line-before": [
      "always",
      {
        ignore: ["after-comment", "first-nested"]
      }
    ],
    "unit-no-unknown": [true, { ignoreUnits: ["rpx"] }],
    "order/order": [
      [
        "dollar-variables",
        "custom-properties",
        "at-rules",
        "declarations",
        {
          type: "at-rule",
          name: "supports"
        },
        {
          type: "at-rule",
          name: "media"
        },
        "rules"
      ],
      { severity: "warning" }
    ]
  },
  ignoreFiles: ["**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx", "report.html"]
};
