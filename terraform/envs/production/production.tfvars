environment        = "production"
aws_region         = "us-east-1"
domain_name        = "app.example.com"
nat_count          = 2
multi_az           = true
rds_instance_class = "db.t4g.medium"
api_replicas       = 3
next_replicas      = 3
worker_replicas    = 2

# Populated by CI/CD: set via -var at apply time.
# image_backend  = "123456789012.dkr.ecr.us-east-1.amazonaws.com/momentum-backend:<sha>"
# image_frontend = "123456789012.dkr.ecr.us-east-1.amazonaws.com/momentum-frontend:<sha>"
