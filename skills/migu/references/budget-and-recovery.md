# 预算台账与提交恢复

项目本地使用 SQLite 台账记录预算预留、提交和恢复，文件放在当前客户项目（建议 `evidence/ledger.sqlite`），不放进 skill、仓库或工具箱。台账只存账户代号、渠道代号、幂等键、请求哈希、金额和状态，不写密钥、Cookie、登录态或完整配置。

使用 `skills/migu/scripts/ledger.py`。测试和预检不得提交付费生成。

## 预算预留

先把已授权预算写入台账，再按本次请求预留金额。可用额度 = 已授权 − 已预留 − 已花费。额度不足时停止提交，说明缺口，不擅自降低复刻质量或改走图文。成功后把预留转为实花，实花不得超出已授权预算，否则先补预算再确认，禁止静默透支。从未向供应商发出的 `reserved` 可用 `release` 取消。已发出但结果不明的记录不能 `release`，查清后走 `confirm_success` 或 `confirm_failure`。

## 幂等键与重复提交保护

每一次准备发给供应商的图片或视频请求都要有稳定幂等键，键绑定请求哈希（模型、镜头、时长、参考等）。同一幂等键、同一请求只预留一次，重复调用返回原记录，不得再向供应商提交。同一键配上不同请求直接拒绝。已成功或已提交的键禁止重投。

超时先查询，不能把再次 `build` 或再次 HTTP 提交当作轮询。

## 受理未知

没拿到任务 id、终端断开、或无法判断远端是否已经受理时，把该键标为 `submission_unknown`。在查清之前禁止用同一键或同一请求再提交，以免重复扣费。先用渠道查询/对账恢复；确认失败后走 `confirm_failure` 释放预留（不是 `release`），再用**新的**幂等键在剩余预算内先 `reserve` 再提交。确认成功则走 `confirm_success` 记下实花和任务 id。向供应商提交前必须先有 `reserved` 记录；`assert_can_submit` 在无记录或状态为 failed/released 时拒绝，`reserved` 允许第一次提交，`submitted`、`succeeded`、`submission_unknown` 禁止。

不要把“生成成功”或供应商 returned succeeded 当成整单完成，见 [检查与剪辑交接](qa-and-editing.md)。
