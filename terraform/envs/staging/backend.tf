# Staging remote state (bootstrap: terraform-bootstrap/).
terraform {
  backend "s3" {
    bucket         = "momentum-tf-state"
    key            = "staging/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
