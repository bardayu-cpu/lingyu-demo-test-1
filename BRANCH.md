# hf-screening 分支说明

- 基线：`gpt-fix-b7`（demo-v2.0，含 B1–B7 修复）。完整源码在 `_src/`，根目录 `index.html` 是打包产物。
- 本分支范围：筛查与危机相关逻辑。
  - 学生端：`_src/学生端/src/rules.js`（量表分段、风险题、危机词）、`intake.js`（小屿访谈）
  - 机构端：危机 / 风险信号的展示与处理（如 `a3_people.js`、`a23_v118.js`、`a24_v119.js` 中相关部分）
- 共用文件需先和产品负责人确认再改：`_src/*/src/data.js`、各 `build.py`、`_src/试用版外壳/`、`_src/自动测试/` 中的公共支持脚本。
- 改完请跑 `_src/自动测试/` 下的回归，再提 PR 合回，不要直接推 `main`。
