# After milestone 20: safe training worker

Milestone 20 adds opt-in local staging of already approved JPEG/PNG and YOLO labels, checks source and staged SHA-256 fingerprints, rejects destination reuse and source-inside-destination mistakes, applies byte/file caps, and attempts read-only file permissions. Tests use generated synthetic images.

**Security limits:** POSIX chmod is not immutable storage. A privileged process, concurrent writer, or hostile filesystem can still alter files. The copy is not atomic and there is no sandbox, no OS-enforced read-only mount, no worker isolation and no robust race-free openat directory traversal. The stage is not yet safe to hand to an untrusted training worker. Future work: isolated read-only mount or content-addressed snapshot, immutable file descriptor / openat traversal, run consent, no-network training environment, pinned model artifacts, CPU/GPU quotas and independent field evaluation.

No training, model downloads, external transfers, cloud resources, customer images or EL processing in this milestone.
