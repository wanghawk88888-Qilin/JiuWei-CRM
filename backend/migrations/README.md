# JiuWei CRM — Database Migrations

生产环境运行的是**含真实业务数据的 SQLite 数据库**。本目录下的所有迁移脚本遵守同一条铁律：

> 只做加法。永不 DROP / DELETE / TRUNCATE / 重建表 / 覆盖数据。

---

## v0.2.1 — Resume Batch Import

脚本：`v0_2_1_resume_batch_import.py`

### 变更内容

**新增表**

| 表 | 说明 |
|---|---|
| `resume_import_batches` | 批次主表。由 `Base.metadata.create_all` 创建，不触碰任何已有表 |

**新增列（全部 nullable、无默认值、旧数据读出为 NULL）**

| 表 | 列 | 类型 |
|---|---|---|
| `import_logs` | `batch_id` | INTEGER |
| `import_logs` | `error_code` | VARCHAR(50) |
| `lead_drafts` | `batch_id` | INTEGER |
| `lead_drafts` | `name_confidence` | VARCHAR(20) |
| `lead_drafts` | `phone_confidence` | VARCHAR(20) |
| `lead_drafts` | `conflict_flags` | TEXT |
| `lead_drafts` | `duplicate_lead_id` | INTEGER |

**新增索引**：`ix_import_logs_batch_id`、`ix_lead_drafts_batch_id`

唯一使用的 DDL 是 `ALTER TABLE ... ADD COLUMN` 与 `CREATE INDEX IF NOT EXISTS`。

### 幂等性

脚本先读 `PRAGMA table_info` 判断列是否已存在：

- 全新数据库 → `create_all` 已建好，脚本判定"无需变更"直接退出
- 已执行过 → 判定"schema 已是 v0.2.1"直接退出
- 只补齐缺失部分 → 不会重复 ALTER

同一套加列逻辑（`app/core/db_migrations.py`）只由本迁移脚本显式调用。后端
启动时**不再**自动执行任何 schema 变更——`create_all` 只创建缺失的表、从不
修改已有表，因此生产库的 v0.2.1 列升级必须显式运行本脚本。

### 执行方式

```bash
# 干跑：只报告缺什么，不做任何修改
docker compose exec backend python -m migrations.v0_2_1_resume_batch_import --check

# 正式执行（自动备份 SQLite 文件 + 迁移前后行数比对）
docker compose exec backend python -m migrations.v0_2_1_resume_batch_import
```

脚本会自动：

1. 用 SQLite 官方 backup API（`sqlite3.Connection.backup`）生成一致性快照
   `data/jiuwei_crm.db.bak-v0.2.1-<时间戳>`，不停止/删除/重建生产库；
   备份完成后校验文件存在且可正常打开（`PRAGMA quick_check`）
2. 打印迁移前各业务表行数
3. 执行加列
4. 打印迁移后行数，并在任何一张表行数减少时以非 0 退出码报警

退出码：`0` 成功 / `1` --check 检测到需要迁移 / `2` 检测到数据丢失 / `3` 迁移未完成 / `4` 备份失败（无可靠备份时拒绝改 schema）

### 回滚

**首选：不回滚 schema。**

新增列全部 nullable，且 v0.2.0 的代码从不读写它们；`resume_import_batches`
是一张 v0.2.0 完全不感知的独立新表。因此把应用回退到 v0.2.0 之后，
库里多出的列和表是惰性的，不影响任何旧功能。回滚应用即可：

```bash
git checkout <v0.2.0 的 commit>
docker compose build backend frontend
docker compose up -d
```

**如果确实需要恢复数据库文件**（例如迁移过程中断电）：

```bash
docker compose stop backend
cp backend/data/jiuwei_crm.db.bak-v0.2.1-<时间戳> backend/data/jiuwei_crm.db
docker compose start backend
```

**注意**：SQLite 不支持 `ALTER TABLE DROP COLUMN`（3.35 以下）。不要尝试手工删列
——那需要重建表，正是本项目禁止的操作。多余的列留着没有任何代价。
