# Security Policy

Compass starts as a local browser workspace. Shared workspaces send decision records to the configured Compass server. The server stores workspace access tokens as SHA-256 hashes and rejects stale writes with revision checks.

Running a Jev readiness check sends the selected decision record and its computed completion metadata to the configured TypeSafe API. Jev does not choose an outcome. Teams should review TypeSafe's data terms before enabling the integration and should protect their `TYPESAFE_API_KEY`, Compass database, workspace IDs, and workspace access tokens.

The bundled SQLite setup is intended for one trusted server instance. Internet-facing deployments should terminate TLS at a reverse proxy, restrict allowed origins, back up `/data`, and use platform-level request throttling.

Please report security issues privately through GitHub's security advisory feature. Do not open a public issue for an undisclosed vulnerability.

Only the latest release is supported with security fixes.
