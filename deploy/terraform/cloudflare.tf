# Cloudflare DNS & Tunnel configuration for zksato

variable "cloudflare_hostname" {
  description = "Hostname for zksato routing"
  type        = string
  default     = "zksato.zeaz.dev"
}

variable "cloudflare_tunnel_target" {
  description = "Target address or tunnel UUID for CNAME record"
  type        = string
  default     = "45667e7e-7383-4265-b53e-6a9e770a8554.cfargotunnel.com"
}

resource "cloudflare_dns_record" "zksato_cname" {
  count   = var.cloudflare_zone_id != null ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = "zksato"
  content = var.cloudflare_tunnel_target
  type    = "CNAME"
  proxied = true
  ttl     = 1
  comment = "zksato production entrypoint routed to Cloudflare Tunnel"
}
