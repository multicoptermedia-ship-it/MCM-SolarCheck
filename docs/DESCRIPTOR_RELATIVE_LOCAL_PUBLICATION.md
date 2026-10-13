# POSIX descriptor-relative publication prototype

`open_private_directory_chain` opens a trusted absolute root and its customer/project children using `O_DIRECTORY | O_NOFOLLOW`, returning an open project directory descriptor. The caller closes it. This prevents traversal through symbolic links in customer/project components at the moment they are opened, and pins the directory inode against later pathname replacement.

`DescriptorRelativePublisher` verifies the source file by streaming its size and SHA-256 and exclusively creates a final hard link relative to the pinned destination directory descriptor. It fsyncs that directory after link creation. Existing destination names are never replaced.

**Limitations:** These are standalone POSIX prototypes, not wired into `CanonicalReservedLocalPublication` or IONOS SFTP. The trusted root's *ancestors* are not opened component-by-component; source path and source immutability are not fully pinned against concurrent rename/writes; the final hard link shares the source inode and can be modified by a process with write access. Restrict source and destination permissions, ensure a trusted local filesystem, perform post-publish readback and journal reconciliation, and test crash/host concurrency before production. Windows and generic SFTP do not guarantee these POSIX semantics.
