# 烘焙拼批追溯台深度登记

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 批次秤单采信 | 看毛皮重规范、重复秤单和隔离行 | `/api/lots/weighins` | `app/modules/weighins/reader.py` `app/modules/weighins/normalize.py` `app/modules/weighins/dedup.py` | `tests/test_weighins.py` |
| M2 投入来源核验 | 核对来源存量、抢占与实领回执裁决 | `/api/lots/supply` | `app/modules/supply/reservations.py` `app/modules/supply/service.py` | `tests/test_supply.py` |
| M3 拼批图比例传递 | 逐边复查产地克重、循环和待证来源 | `/api/lots/lineage` | `app/modules/lineage/cycles.py` `app/modules/lineage/mix.py` `app/modules/lineage/service.py` | `tests/test_lineage.py` |
| M4 灌装与返料归并 | 比对净重、占用和可用返料 | `/api/lots/packing` | `app/modules/packing/budget.py` `app/modules/packing/settle.py` | `tests/test_packing.py` |
| M5 重量守恒追溯 | 对平工作批、仓内和各产地账 | `/api/lots/balance` | `app/modules/balance/service.py` `app/modules/balance/stock.py` | `tests/test_balance.py` |
| M6 批次留档复跑 | 查在柜卷联、按原件复算 | `/api/runs` | `app/modules/runs/cabinet.py` `app/modules/runs/service.py` | `tests/test_runs.py` |
| M7 配方证据签发 | 从包装号取经过校验的来料证据 | `/api/export/<id>` | `app/modules/proof/recall.py` `app/modules/proof/service.py` | `tests/test_proof.py` |

## 陷阱登记

| TRAP | 现象 | 朴素处理后果 | 本项目规则 | 位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-02 | 投入表开头 BOM | 首字段不符 | 读取前去 BOM | `app/modules/weighins/reader.py` | `tests/test_weighins.py::test_bom` |
| TRAP-04 | 重复投入表头 | 混入投入量 | 记分段 | `app/modules/weighins/reader.py` | `tests/test_weighins.py::test_segment` |
| TRAP-05 | 秤单有多余列 | 滚入错位列 | 按原行隔离并保留工作批 | `app/modules/weighins/reader.py` | `tests/test_weighins.py::test_bad_width` |
| TRAP-07 | 投料 N/A | 当零重量 | 留原值且归为缺项 | `app/modules/weighins/normalize.py` | `tests/test_weighins.py::test_sentinel` |
| TRAP-10 | 两级拼批出现小数克 | 份额逐次截断 | 有理数逐边传播 | `app/modules/lineage/mix.py` | `tests/test_lineage.py::test_multi_parent_mix_exact` |
| TRAP-14 | 同号秤单不同重量 | 后写覆盖 | 隔离全部冲突行 | `app/modules/weighins/dedup.py` | `tests/test_weighins.py::test_conflict_removed` |
| TRAP-15 | 同包装秤单使用 kg 和 g | 重计或误判冲突 | 归一后精确判重 | `app/modules/weighins/mass.py` `app/modules/weighins/dedup.py` | `tests/test_weighins.py::test_unit_normalized_duplicate` |
| TRAP-19 | 两张返料申请独立看均够 | 按提交顺序抢占 | 总额超限则整组隔离；凭实领回执整组裁决，不按先到先认 | `app/modules/supply/reservations.py` | `tests/test_supply.py::test_global_overdraw_no_first_claim` `tests/test_supply.py::test_overdraw_resolved_by_receipts` |
| TRAP-20 | 双向返料引用 | 顺序无法确定 | 提取循环分量和实际路径 | `app/modules/lineage/cycles.py` | `tests/test_lineage.py::test_actual_cycle` |
| TRAP-21 | 实领与申请克重不符 | 仍按申请额核销导致错料入下游 | 按实领额建边核销，`RECEIPT_VARIANCE` 留痕不阻断，守恒按实领勾稽 | `app/modules/lineage/service.py` `app/modules/packing/settle.py` | `tests/test_lineage.py::test_receipt_variance_is_informational` `tests/test_balance.py::test_receipt_batches_conserve_on_admitted_mass` |
| TRAP-22 | 晚到回执先挂起、后补齐 | 覆盖已签原件或重复出签件 | 补齐后另存新指纹归档，旧件凭封缄仍可验，同材料重跑不新增 | `app/modules/runs/service.py` `app/modules/proof/service.py` | `tests/test_runs.py::test_late_receipt_creates_new_archive_keeps_old` |

库内可信核销 1670 g = 1485 g 灌装 + 75 g 损耗 + 105 g 工作批余料 + 5 g 未领返料。4 个未通过工作批（BA-07、BA-08、BA-09、BA-10）合计 270 g 分批列待证。RT-A 300 g = 180 g 给 BA-02 + 120 g 给 BA-03。RT-D 申请 120 g 超卷重 100 g，两张回执实领 50 g + 45 g = 95 g 后整组放行：BA-05 实领 50 g（灌装 40 g、余 10 g），BA-06 实领 45 g（灌装 40 g、余 5 g），卷内剩 5 g；PK-E、PK-F 进入可签，PK-G 仍待证。PK-C 275 g = 巴西 185.46 g + 哥伦比亚 17.6 g + 埃塞 71.94 g。
