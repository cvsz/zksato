resource "aws_kms_key" "app_encryption_key" {
  description             = "KMS key for application data encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Environment = var.environment
  }
}

resource "aws_kms_alias" "app_encryption_alias" {
  name          = "alias/app-encryption-key-${var.environment}"
  target_key_id = aws_kms_key.app_encryption_key.key_id
}
