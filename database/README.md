# Database deployment notes

The local compose setup uses MySQL InnoDB with GTID and row-based binary logging enabled, and MongoDB as a single-node replica set so transactions/change streams can be developed against a replica-set topology. SQL patient payloads are AES-256-GCM encrypted before insert; only an HMAC-SHA-256 pseudonym is used as the lookup key. MongoDB audit documents are encrypted before insert and validated by the initialization script.

This is not a high-availability deployment. A single MySQL server with binary logging cannot fail over on its own, and a one-member MongoDB replica set has no independent voting member. Production needs a managed or orchestrated MySQL HA cluster (for example, InnoDB Cluster with at least three members and a Router/failover policy), MongoDB replica-set members in separate failure zones, TLS and authenticated least-privilege database users, tested point-in-time backups and restores, monitoring, and a managed secrets/key-rotation process. Do not mount local database volumes into shared or untrusted hosts.

`init.sql` is run only when the MySQL data directory is first initialized. Use a reviewed, versioned migration process to change an existing database; initialization scripts are not migrations.
