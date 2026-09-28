# Ansible post-migration validation

Migration Factory can export a no-secret Ansible validation pack for the currently imported migration estate.

## API

`GET /api/v1/reports/ansible-validation-pack.zip`

The pack uses the official `nutanix.ncp` collection plus standard Ansible/Windows modules to validate:

- Prism Central cluster visibility
- Linux guest connectivity and facts
- Windows WinRM connectivity
- hostname evidence
- expected migration wave and target-network metadata

Guest IP addresses are intentionally exported as placeholders and credentials are never embedded. Use Ansible Vault or an external secret manager for runtime authentication.

This is post-migration technical validation, not application UAT.