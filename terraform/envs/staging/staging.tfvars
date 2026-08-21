environment        = "staging"
aws_region         = "us-east-1"
domain_name        = ""
nat_count          = 1
multi_az           = false
rds_instance_class = "db.t4g.micro"
api_replicas       = 2
next_replicas      = 2
worker_replicas    = 1

# Populated by CI/CD: set via -var at apply time.
# image_backend  = "123456789012.dkr.ecr.us-east-1.amazonaws.com/momentum-backend:<sha>"
# image_frontend = "123456789012.dkr.ecr.us-east-1.amazonaws.com/momentum-frontend:<sha>"
