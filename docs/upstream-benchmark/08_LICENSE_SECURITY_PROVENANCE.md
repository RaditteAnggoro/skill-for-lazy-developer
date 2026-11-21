# 08 — License, security and provenance

**Decision: accept with constraints for static comparison and independent local design.** Runtime adoption, redistribution, and host installation require separate review. The report links source by commit and paraphrases capabilities. The local changes are original implementations, with no copied upstream code, rulebook, prompts, or fixture material.

| Source | License anchor or status | Review boundary |
| --- | --- | --- |
| DietrichGebert/ponytail | MIT · [LICENSE](https://github.com/DietrichGebert/ponytail/blob/96608e078b2d5ea607c5c3b8b5a54d1c1fba6846/LICENSE) | Works without an extra hook only as guidance; hooks require host install |
| obra/superpowers | MIT · [LICENSE](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/LICENSE) | Instruction compliance and hook loading depend on host |
| mattpocock/skills | MIT · [LICENSE](https://github.com/mattpocock/skills/blob/abeeaf95660ba9e8b7c753eb38f441ca707a8823/LICENSE) | Discussion depth is inappropriate for trivial changes |
| humanlayer/skills | MIT · [LICENSE](https://github.com/humanlayer/skills/blob/4d69d20f6e9b57b4fcf0d501ccfb1be961f0f329/LICENSE) | Automated sessions need host support; manual fallback possible |
| tt-a1i/archify | Apache-2.0 · [LICENSE](https://github.com/tt-a1i/archify/blob/8509a3d63e763b4d454ea9aafa1f939545fcb1ea/LICENSE) · [NOTICE](https://github.com/tt-a1i/archify/blob/8509a3d63e763b4d454ea9aafa1f939545fcb1ea/NOTICE) | A valid diagram describes supplied data; source relationships need independent evidence |
| ChromeDevTools/chrome-devtools-mcp | Apache-2.0 · [LICENSE](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/437f394edcb0708d60637bcd326c59b4351f35ef/LICENSE) | Authenticated pages and debugging output may contain private data |
| akitaonrails/ai-memory | MIT · [LICENSE](https://github.com/akitaonrails/ai-memory/blob/6a141858bb88fbd025b144664a37271acd5e0e43/LICENSE) | Bridge connectivity, scope, and trust still depend on deployment |
| Gentleman-Programming/engram | MIT · [LICENSE](https://github.com/Gentleman-Programming/engram/blob/380d513841f0cc96f87088b837156d758bd1ee4c/LICENSE) | Provider output requires context filtering and repo-specific trust checks |
| rtk-ai/rtk | Apache-2.0 · [LICENSE](https://github.com/rtk-ai/rtk/blob/ef0b734b6b2f5df26267bf05d90d71b887658580/LICENSE) | Formatting can remove details required for an investigation |
| mksglu/context-mode | Elastic-2.0 (root text) · [LICENSE](https://github.com/mksglu/context-mode/blob/8a61fa7ba461d5474bac35b5f6700ed598e7022f/LICENSE) | Persistence and executing tools must honor policy; no host rehearsal here |
| oraios/serena | GPL-3.0-or-later app; MIT SolidLSP · [LICENSE](https://github.com/oraios/serena/blob/7f7d6245bf96b60fdf4e752a779917372fd1ee6e/LICENSE) | Dynamic/reflection/SQL edges can be unresolved |
| yamadashy/repomix | MIT · [LICENSE](https://github.com/yamadashy/repomix/blob/f0bcc08ab07d2dff2415fa40fb26d07eaf55b4ff/LICENSE) | A scan does not authorize sending packed content elsewhere |
| nextlevelbuilder/ui-ux-pro-max-skill | MIT · [LICENSE](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/f76d1653d7467fc11fb9d9d79295a421c92ab958/LICENSE) | Recommendations need project conventions and operator validation |
| vercel-labs/agent-skills | Component terms unverified | Rules are not browser evidence and remote lookup needs permission/data boundaries |
| miqdadbadjuber/anti-slop | MIT · [LICENSE](https://github.com/miqdadbadjuber/anti-slop/blob/7f6a03df2931c12cb244dc4ab14ee4866b0ac2ba/LICENSE) | Rule compliance is subjective and varies by product context |
| heydamir/unslop | CC-BY-4.0 · [LICENSE](https://github.com/heydamir/unslop/blob/620163eedb3529d9cd23a3994ed8d287d06f760d/LICENSE) | No observed independently graded UX run here |
| hannsxpeter/humanizer | MIT · [LICENSE](https://github.com/hannsxpeter/humanizer/blob/e8f1248a7d4919689c1f942e356ed95b102d9f07/LICENSE) | Stylistic edits can change meaning; factual preservation must be tested |
| pbakaus/impeccable | Apache-2.0 · [LICENSE](https://github.com/pbakaus/impeccable/blob/b49177d32788f2dc585c42831d845dacf1ebed2c/LICENSE) · [NOTICE.md](https://github.com/pbakaus/impeccable/blob/b49177d32788f2dc585c42831d845dacf1ebed2c/NOTICE.md) | Account/network sync is a separate trust boundary |
| lzehrung/codegraph | MIT · [LICENSE](https://github.com/lzehrung/codegraph/blob/13687be6a1e875b1153137025559488c4fbb28c6/LICENSE) | Index freshness and unsupported dynamic edges affect completeness |
| Graphify-Labs/graphify | Apache-2.0 · [LICENSE](https://github.com/Graphify-Labs/graphify/blob/b582ad401aaef4378935ec6620e3b165ae8e03c1/LICENSE) · [NOTICE](https://github.com/Graphify-Labs/graphify/blob/b582ad401aaef4378935ec6620e3b165ae8e03c1/NOTICE) | Semantic processing or visualization needs separate dataflow review |
| trailofbits/skills | CC-BY-SA-4.0 · [LICENSE](https://github.com/trailofbits/skills/blob/149d7b21f4067765b82e67029730b42d228ef4b4/LICENSE) | Test presence alone does not verify execution or authorize security probing |
| getsentry/skills | Apache-2.0 · [LICENSE](https://github.com/getsentry/skills/blob/a582c51ee29d0f35e6ac321340796f77d43da733/LICENSE) | Review coverage depends on available configuration and evidence |
| promptfoo/promptfoo | MIT · [LICENSE](https://github.com/promptfoo/promptfoo/blob/e6d8f04a6c0f3fa9d44345fd6eba081c1a6b07ad/LICENSE) | External calls/cost and uneven coverage need separate configuration |
| NousResearch/hermes-agent | MIT · [LICENSE](https://github.com/NousResearch/hermes-agent/blob/52b527194b364ba073c85f0b1cd8c63bc9264cac/LICENSE) | Permissions and lifecycle behavior depend on configured host/runtime |

- For future redistribution, retain applicable notices for MIT/Apache material, verify per-file and bundled notices, and review attribution/share-alike obligations for CC material. Review Serena and Context Mode at component level. Confirm Vercel component terms before adaptation. No reliance on metadata alone should authorize redistribution.
- Repomix and context indexing handle repository contents. Keep snapshots scoped and local, honor data classification, and separately review persistence, cleanup and egress. Browser tools can expose active session data and network payloads. Use synthetic accounts and explicitly scoped development targets.
- Hermes, ai-memory, Engram, Context Mode, Codegraph and Graphify expose executable or persistent surfaces. Their source includes integrations and dependencies beyond the inspected paths. Treat unreviewed binaries and transitive dependencies as out of scope for activation.
- Impeccable account/sync is separate from using a rubric. No sync, sign-in, hooks, or plugin install was attempted. Promptfoo can use external evaluation providers, and the local benchmark uses no provider from its distribution.
- For security skill collections, this review sampled defensive specification checks, testing, and policy handling. No offensive workflows were executed or adopted.
- Any future optional integration needs a pinned artifact, permission and data-flow review, isolated canary, fallback, and removal procedure. Current rollback is independent of the upstream checkout directories.

Reproduce a source anchor using the manifest and `git -C <clone> show <sha>:<tracked-path>`. If a historical pin is needed, use the recorded `refs/benchmark/pinned/<sha>` ref. Distinguish a pinned location, a statically inspected capability, and an actual execution result.
