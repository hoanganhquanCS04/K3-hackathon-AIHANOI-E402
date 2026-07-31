# Eval run — technical-baseline

- Git commit: `4c44b00279fcfd87e13d1f0bdef9bcf8248a8b8a`
- Cases: **20**
- Technical pass: **5/20 (25.0%)**
- Official quality bar: **pending_human_input**
- Fake-citation cases: **0**
- Student-attribution cases: **0**
- Query not implemented: **6**
- Missing summary artifact: **2**

## Từng case

| Case | Actual | Technical | Official | Blocker |
|---|---|---:|---:|---|
| `SUM-T01` | `ok` | False | pending | Human gold ideas are incomplete. |
| `SUM-T02` | `ok` | False | pending | Human gold ideas are incomplete. |
| `SUM-T03` | `ok` | False | pending | Human gold ideas are incomplete. |
| `SUM-T04` | `ok` | False | pending | Human gold ideas are incomplete. |
| `SUM-T05` | `missing_artifact` | False | pending | M2 artifact missing: D:\AI\AI_thuc_chien\Lab\Batch03-2A202601875-HoangAnhQuan\summarizer\artifacts\summaries\T05\session.json |
| `SUM-T06` | `missing_artifact` | False | pending | M2 artifact missing: D:\AI\AI_thuc_chien\Lab\Batch03-2A202601875-HoangAnhQuan\summarizer\artifacts\summaries\T06\session.json |
| `AMB-001` | `needs_clarification` | True | True |  |
| `AMB-002` | `needs_clarification` | False | False |  |
| `SRC-001` | `not_implemented` | False | pending | M2/M1 query guardrail is not connected. |
| `RARE-001` | `not_implemented` | False | pending | M2/M1 query guardrail is not connected. |
| `OOS-001` | `out_of_scope` | True | True |  |
| `SRC-002` | `needs_clarification` | False | False |  |
| `SRC-003` | `needs_clarification` | True | True |  |
| `RARE-002` | `needs_clarification` | True | True |  |
| `AMB-003` | `not_implemented` | False | pending | M2/M1 query guardrail is not connected. |
| `NORMAL-001` | `needs_clarification` | False | False |  |
| `SRC-004` | `not_implemented` | False | pending | M2/M1 query guardrail is not connected. |
| `OOS-002` | `refused` | True | True |  |
| `DOM-001` | `not_implemented` | False | pending | M2/M1 query guardrail is not connected. |
| `DOM-002` | `not_implemented` | False | pending | M2/M1 query guardrail is not connected. |

## Blocker

- Not every case has an official human-reviewed verdict.

> Đây là technical baseline nếu official verdict còn pending. Không đưa tỷ lệ
> technical vào form như kết quả golden set chính thức.
