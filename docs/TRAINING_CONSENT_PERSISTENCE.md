# Online training consent persistence

The online persistence builder now creates the SQLite consent event store in its private database. The online service composition checks project ownership before recording consent, and the HTTP entrypoint uses the composed service by default.

Remaining work: atomic upload/audit handling, authenticated withdrawal endpoint, complete privacy notice, training-data selection, and retention automation. A stored upload without a recorded grant must never be treated as training permission. No automated training is enabled.
