# Security Notes

- Use a dedicated least-privilege Prism Central service identity.
- Never commit Prism credentials to Git.
- TLS verification is enabled by default.
- Treat RVTools exports as sensitive infrastructure data.
- Sanitize customer names, IP addresses and application annotations before publishing examples.
- The MVP Prism connector is read-only.
- Add SSO/OIDC, application RBAC and secret-manager integration before enterprise multi-user deployment.
