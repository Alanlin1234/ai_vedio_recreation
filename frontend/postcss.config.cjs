/** PostCSS 独立为 CJS，避免在 vite.config 内联时部分环境解析失败导致 /src/main.jsx 转换 500 */
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
