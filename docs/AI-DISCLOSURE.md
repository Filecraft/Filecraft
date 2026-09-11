# AI development disclosure

Filecraft is developed with AI assistance. The maintainer identifies the development model as **OpenAI's frontier model GPT-6 Astra**. This describes the development process, not an AI feature inside Filecraft. Filecraft does not ship a trained neural processing engine, and local document processing does not send files to this model.

## Maintainer-supplied model metrics — not audited

The maintainer supplied this dashboard transcription. Values are preserved exactly rather than silently repaired:

| Supplied label | Supplied value |
| --- | --- |
| Model metrics | 1M |
| Total requests | 1.99K |
| Total token count | 1.84M |
| Average per request (total) | 65,916 avg per request |
| Estimated total cost | $256.09 |
| Input tokens | 129.97M |
| Average per request (input) | 65,475 avg per request |
| Output tokens | 876.04K |
| Average per request (output) | 441 avg per request |

These figures contain inconsistencies: the supplied input token count alone exceeds the supplied total token count. The meaning of “Model metrics 1M,” reporting interval, currency and billing adjustments were not independently established. This is a static, maintainer-supplied disclosure—not live telemetry, a verified invoice, or a cost/performance guarantee. No visitor analytics are collected to update it.

AI-generated changes still require human accountability, source/license review, regression tests and independent verification. See [AI contribution guidelines](../AGENTS.md).
