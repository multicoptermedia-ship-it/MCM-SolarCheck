# Private streamed part assembly (prototype)

`PrivatePartAssembler` streams immutable remote parts in index order into a uniquely named temporary file in a caller-supplied **existing private directory**. Each part is checked against its stored size and SHA-256; the assembled byte stream is checked against the complete file size and SHA-256. The temporary file is flushed and fsynced before returning. On a detected error, it is deleted. The caller owns cleanup of a successfully returned temporary file.

`AuthorizedPrivatePartAssembly` checks canonical transfer ownership, pending state, expected size and complete SHA-256. The caller still supplies expected part count; it must be made canonical before production. This prototype does **not** publish, rename into a customer-visible location, send email, charge, or trigger processing.

Security limits: directory must be trusted and private (not writable by untrusted users); parent symlinks and directory replacement are not fully defended. Disk space must be reserved/limited; a crash may leave orphaned `.assembly-*` files requiring cleanup. The remote part backend must actually enforce immutability and ownership, and concurrent modification must be prevented. Add durable publish state, exclusive publish and post-publish verification, cancellation and crash recovery before production. No live IONOS SFTP access is implemented.
