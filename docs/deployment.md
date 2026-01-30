# Deployment Guide

> Deploying WAASP to AWS

## Overview

This guide covers deploying WAASP to AWS with:
- ECS Fargate (containers)
- RDS PostgreSQL (database)
- ElastiCache Redis (Celery broker)
- Application Load Balancer

---

## Architecture

```mermaid
flowchart TB
    subgraph Internet
        R53["🌐 Route 53<br/>api.example.com"]
        CF["☁️ CloudFront (opt)<br/>CDN + WAF"]
    end
    
    subgraph VPC["AWS VPC"]
        ALB["⚖️ Application<br/>Load Balancer"]
        
        subgraph ECS["ECS Cluster"]
            subgraph Web["Web Tasks"]
                W1["🌐 Web 1"]
                W2["🌐 Web 2"]
                W3["🌐 Web 3"]
            end
            
            subgraph Workers["Worker Tasks"]
                WK1["⚙️ Worker 1"]
                WK2["⚙️ Worker 2"]
            end
        end
        
        subgraph Data["Data Layer"]
            RDS[("🐘 RDS<br/>PostgreSQL")]
            Redis[("🔴 ElastiCache<br/>Redis")]
            S3["📦 S3<br/>Logs"]
        end
    end
    
    R53 --> CF --> ALB
    ALB --> W1 & W2 & W3
    W1 & W2 & W3 --> RDS & Redis
    WK1 & WK2 --> RDS & Redis & S3
    Redis --> WK1 & WK2
```

---

## Prerequisites

### AWS CLI Setup

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure
aws configure
# Enter: Access Key, Secret Key, Region (eu-west-2), Output format (json)
```

### ECR Repository

```bash
# Create repository
aws ecr create-repository --repository-name waasp --region eu-west-2

# Login to ECR
aws ecr get-login-password --region eu-west-2 | \
    docker login --username AWS --password-stdin \
    <account-id>.dkr.ecr.eu-west-2.amazonaws.com
```

---

## Build & Push Docker Image

```bash
# Build production image
docker build --target production -t waasp:latest .

# Tag for ECR
docker tag waasp:latest \
    <account-id>.dkr.ecr.eu-west-2.amazonaws.com/waasp:latest

# Push
docker push <account-id>.dkr.ecr.eu-west-2.amazonaws.com/waasp:latest
```

---

## Infrastructure (Terraform)

### Directory Structure

```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── vpc.tf
├── ecs.tf
├── rds.tf
├── elasticache.tf
└── alb.tf
```

### VPC Configuration

```hcl
# vpc.tf
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0"

  name = "waasp-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["eu-west-2a", "eu-west-2b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true  # Cost saving for non-prod
}
```

### ECS Cluster

```hcl
# ecs.tf
resource "aws_ecs_cluster" "main" {
  name = "waasp-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "web" {
  family                   = "waasp-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([
    {
      name  = "waasp"
      image = "${aws_ecr_repository.waasp.repository_url}:latest"
      
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "APP_ENV", value = "production" },
        { name = "DATABASE_URL", value = "postgresql://${var.db_user}:${var.db_pass}@${aws_db_instance.main.endpoint}/waasp" },
        { name = "REDIS_URL", value = "redis://${aws_elasticache_cluster.main.cache_nodes[0].address}:6379/0" },
      ]

      secrets = [
        { name = "SECRET_KEY", valueFrom = aws_secretsmanager_secret.secret_key.arn },
        { name = "API_TOKEN", valueFrom = aws_secretsmanager_secret.api_token.arn },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.waasp.name
          awslogs-region        = var.region
          awslogs-stream-prefix = "web"
        }
      }
    }
  ])
}
```

### RDS PostgreSQL

```hcl
# rds.tf
resource "aws_db_instance" "main" {
  identifier        = "waasp-db"
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = "db.t3.micro"  # Adjust for production
  allocated_storage = 20

  db_name  = "waasp"
  username = var.db_user
  password = var.db_pass

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 7
  skip_final_snapshot     = true  # Set false for production
}
```

### ElastiCache Redis

```hcl
# elasticache.tf
resource "aws_elasticache_cluster" "main" {
  cluster_id           = "waasp-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]
}
```

---

## Environment Variables

### Secrets Manager

```bash
# Create secrets
aws secretsmanager create-secret \
    --name waasp/secret-key \
    --secret-string "$(openssl rand -hex 32)"

aws secretsmanager create-secret \
    --name waasp/api-token \
    --secret-string "$(openssl rand -hex 32)"
```

### Environment Configuration

```bash
# Production environment variables
APP_ENV=production
DEBUG=false
SECRET_KEY=<from-secrets-manager>
DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/waasp
REDIS_URL=redis://elasticache-endpoint:6379/0
CELERY_RESULT_BACKEND=redis://elasticache-endpoint:6379/1
API_TOKEN=<from-secrets-manager>
```

---

## Database Migrations

### ECS Run Task (One-off)

```bash
# Run migration as one-off task
aws ecs run-task \
    --cluster waasp-cluster \
    --task-definition waasp-web \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}" \
    --overrides '{"containerOverrides":[{"name":"waasp","command":["flask","--app","waasp.app:create_app","db","upgrade"]}]}'
```

### CI/CD Migration Step

```yaml
# .github/workflows/deploy.yml
- name: Run migrations
  run: |
    aws ecs run-task \
      --cluster ${{ env.CLUSTER }} \
      --task-definition ${{ env.TASK_DEF }} \
      --overrides '{"containerOverrides":[{"name":"waasp","command":["flask","db","upgrade"]}]}'
```

---

## Deployment Commands

### Manual Deployment

```bash
# Build and push
docker build --target production -t waasp:latest .
docker tag waasp:latest $ECR_URL/waasp:$VERSION
docker push $ECR_URL/waasp:$VERSION

# Update service
aws ecs update-service \
    --cluster waasp-cluster \
    --service waasp-web \
    --force-new-deployment
```

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: eu-west-2
      
      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build and push
        run: |
          docker build --target production -t $ECR_URL/waasp:$GITHUB_SHA .
          docker push $ECR_URL/waasp:$GITHUB_SHA
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster waasp-cluster \
            --service waasp-web \
            --force-new-deployment
```

---

## Monitoring

### CloudWatch Alarms

```hcl
resource "aws_cloudwatch_metric_alarm" "high_5xx" {
  alarm_name          = "waasp-high-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_ELB_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "High 5XX error rate"
  
  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
}
```

### Health Check

```python
@app.get("/health")
def health_check():
    # Check database
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        return {"status": "unhealthy", "db": "down"}, 503
    
    return {"status": "healthy", "version": __version__}
```

---

## Cost Estimation

| Service | Size | Monthly Cost (approx) |
|---------|------|----------------------|
| ECS Fargate (2 tasks) | 0.25 vCPU, 0.5GB | $15 |
| RDS PostgreSQL | db.t3.micro | $15 |
| ElastiCache Redis | cache.t3.micro | $12 |
| ALB | - | $20 |
| NAT Gateway | - | $35 |
| **Total** | | **~$97/month** |

*Costs vary by region and usage. Consider reserved instances for production.*

---

## Scaling

### Auto Scaling

```hcl
resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.web.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}
```

---

*Deployment guide for WAASP v0.1.0*
