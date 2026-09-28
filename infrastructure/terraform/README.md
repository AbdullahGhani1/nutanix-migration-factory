# Terraform integration

Migration Factory can export a reviewable Nutanix Terraform pack from the currently imported migration estate.

The generated bundle uses the official `nutanix/nutanix` provider and the `nutanix_virtual_machine_v2` resource surface. VM creation is gated by `enable_vm_creation = false` by default.

This export is intentionally **not** an alternative to Nutanix Move for VMware-to-AHV migrations. It exists to operationalize the Infrastructure-as-Code side of Nutanix engineering while keeping migration execution separate from provisioning.

## API

`GET /api/v1/reports/terraform-pack.zip`

The ZIP contains:

- `README.md`
- `versions.tf`
- `provider.tf`
- `variables.tf`
- `locals.tf`
- `planned_vms.tf`
- `outputs.tf`
- `terraform.tfvars.example`
- `inventory.json`
- `manifest.json`

Run `terraform init`, `terraform fmt -check`, `terraform validate`, and a reviewed `terraform plan` before any approved apply in an authorized environment.