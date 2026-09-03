# Security policy

## Supported version

Security fixes currently target the latest commit on `main`.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository. Do not include credentials, private screenshots, real memory exports or personal graph data in a public issue.

Include the affected version, impact, minimal reproduction and any suggested mitigation. You should receive an acknowledgement within seven days.

## Deployment assumptions

Neural Memory is designed for one trusted user on a local machine. The Compose stack binds services to loopback and authenticates private API routes. It has not been hardened as a public multi-tenant service. Do not expose its ports to the internet.
