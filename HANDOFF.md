# HANDOFF

## 待人工

1. **拆分提交**：工作区有大量未提交改动（约 30+ 修改文件 + 多个新增模块 + android_toga 整目录删除），建议人工决定如何拆分提交（候选：①先提「删除 android_toga 废弃实现」单独一笔；②focus_capsule 新功能模块（activity_tracker / daily_progress / process_matching 等）与 Flutter overlay 分笔；③跑测试确认通过后再统一提交）。
2. **推送决定**：本地 main 领先 origin/main 1 个提交，是否推送由人工决定（本轮被禁止 push；且本次 fetch 因网络中断失败，推送前需先确认远端状态）。
3. **新增目录定性**：`focus_app/` 与 `packages/` 为未跟踪的新目录，需人工确认其用途与是否纳入版本控制（或加入 .gitignore）。
