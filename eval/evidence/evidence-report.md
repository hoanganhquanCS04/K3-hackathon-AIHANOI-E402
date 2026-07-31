# Evidence mining report — M3

- Sinh lúc: `2026-07-30T15:46:47.122460+00:00`
- Rules: `v2-locked` (locked)
- Đơn vị đếm: `turn_id`

## Số đếm máy

- Raw rows: **2522**
- Complete turns: **1261**
- Unique users: **369**
- Summary requests: **156 turns / 110 users**
- Whole-session requests: **69 turns / 59 users**
- Summary failure rate: **47.4%**
- Whole-session failure rate: **53.6%**
- Baseline failure rate: **17.7%**

## Kiểm tra tay

- Mẫu đã điền đủ ba nhãn: **40/40**
- Trạng thái: **REVIEW COMPLETE**
- Reviewer: **M3 owner — user-confirmed in Codex**
- `summary` precision=100.0%, recall=100.0%, FPR=0.0%
- `whole_session` precision=100.0%, recall=100.0%, FPR=0.0%
- `failure` precision=100.0%, recall=100.0%, FPR=0.0%

## Cách tái tạo

```powershell
cd eval
uv run python -m m3_eval.mine_chatlog
```
