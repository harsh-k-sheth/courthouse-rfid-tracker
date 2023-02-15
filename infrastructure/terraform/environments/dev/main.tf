# Courthouse RFID Tracking System - AWS Infrastructure
# =====================================================
# Deploys: IoT Core, Lambda, DynamoDB, API Gateway, CloudWatch

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "stage" {
  description = "Deployment stage (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "courthouse-rfid"
}

locals {
  prefix = "${var.project_name}-${var.stage}"
  tags = {
    Project     = var.project_name
    Stage       = var.stage
    ManagedBy   = "terraform"
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = local.tags
  }
}

# ===========================
# DynamoDB Tables
# ===========================

resource "aws_dynamodb_table" "file_locations" {
  name         = "${local.prefix}-file-locations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "tag_id"

  attribute {
    name = "tag_id"
    type = "S"
  }

  attribute {
    name = "case_number"
    type = "S"
  }

  global_secondary_index {
    name            = "case-number-index"
    hash_key        = "case_number"
    projection_type = "ALL"
  }

  tags = {
    Name = "${local.prefix}-file-locations"
  }
}

resource "aws_dynamodb_table" "file_movements" {
  name         = "${local.prefix}-file-movements"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "tag_id"
  range_key    = "timestamp"

  attribute {
    name = "tag_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name = "${local.prefix}-file-movements"
  }
}

resource "aws_dynamodb_table" "readers" {
  name         = "${local.prefix}-readers"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "reader_id"

  attribute {
    name = "reader_id"
    type = "S"
  }

  tags = {
    Name = "${local.prefix}-readers"
  }
}

resource "aws_dynamodb_table" "tags" {
  name         = "${local.prefix}-tags"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "tag_id"

  attribute {
    name = "tag_id"
    type = "S"
  }

  tags = {
    Name = "${local.prefix}-tags"
  }
}

# ===========================
# IAM Role for Lambda
# ===========================

resource "aws_iam_role" "lambda_role" {
  name = "${local.prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${local.prefix}-lambda-dynamodb"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:DeleteItem",
        ]
        Resource = [
          aws_dynamodb_table.file_locations.arn,
          "${aws_dynamodb_table.file_locations.arn}/index/*",
          aws_dynamodb_table.file_movements.arn,
          aws_dynamodb_table.readers.arn,
          aws_dynamodb_table.tags.arn,
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# ===========================
# Lambda Functions
# ===========================

resource "aws_lambda_function" "event_processor" {
  function_name = "${local.prefix}-event-processor"
  role          = aws_iam_role.lambda_role.arn
  handler       = "src.cloud.handlers.event_processor.handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 256

  filename         = "${path.module}/lambda_package.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_package.zip")

  environment {
    variables = {
      STAGE                      = var.stage
      LOCATIONS_TABLE            = aws_dynamodb_table.file_locations.name
      MOVEMENTS_TABLE            = aws_dynamodb_table.file_movements.name
      READERS_TABLE              = aws_dynamodb_table.readers.name
      TAGS_TABLE                 = aws_dynamodb_table.tags.name
      RSSI_WINDOW_SECONDS        = "10"
      RSSI_CONFIDENCE_THRESHOLD  = "6"
    }
  }
}

resource "aws_lambda_function" "location_api" {
  function_name = "${local.prefix}-location-api"
  role          = aws_iam_role.lambda_role.arn
  handler       = "src.cloud.handlers.location_api.handler"
  runtime       = "python3.11"
  timeout       = 10
  memory_size   = 128

  filename         = "${path.module}/lambda_package.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_package.zip")

  environment {
    variables = {
      STAGE           = var.stage
      LOCATIONS_TABLE = aws_dynamodb_table.file_locations.name
      MOVEMENTS_TABLE = aws_dynamodb_table.file_movements.name
      READERS_TABLE   = aws_dynamodb_table.readers.name
      TAGS_TABLE      = aws_dynamodb_table.tags.name
    }
  }
}

resource "aws_lambda_function" "health_monitor" {
  function_name = "${local.prefix}-health-monitor"
  role          = aws_iam_role.lambda_role.arn
  handler       = "src.cloud.handlers.health_monitor.handler"
  runtime       = "python3.11"
  timeout       = 15
  memory_size   = 128

  filename         = "${path.module}/lambda_package.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_package.zip")

  environment {
    variables = {
      STAGE         = var.stage
      READERS_TABLE = aws_dynamodb_table.readers.name
    }
  }
}

# ===========================
# IoT Core
# ===========================

resource "aws_iot_topic_rule" "rfid_events" {
  name        = "${replace(local.prefix, "-", "_")}_events"
  enabled     = true
  sql         = "SELECT * FROM 'courthouse/rfid/events'"
  sql_version = "2016-03-23"

  lambda {
    function_arn = aws_lambda_function.event_processor.arn
  }
}

resource "aws_iot_topic_rule" "rfid_heartbeat" {
  name        = "${replace(local.prefix, "-", "_")}_heartbeat"
  enabled     = true
  sql         = "SELECT * FROM 'courthouse/rfid/heartbeat'"
  sql_version = "2016-03-23"

  lambda {
    function_arn = aws_lambda_function.health_monitor.arn
  }
}

resource "aws_lambda_permission" "iot_events" {
  statement_id  = "AllowIoTInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.event_processor.function_name
  principal     = "iot.amazonaws.com"
  source_arn    = aws_iot_topic_rule.rfid_events.arn
}

resource "aws_lambda_permission" "iot_heartbeat" {
  statement_id  = "AllowIoTInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.health_monitor.function_name
  principal     = "iot.amazonaws.com"
  source_arn    = aws_iot_topic_rule.rfid_heartbeat.arn
}

# ===========================
# API Gateway (REST API)
# ===========================

resource "aws_apigatewayv2_api" "dashboard_api" {
  name          = "${local.prefix}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.dashboard_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "api_lambda" {
  api_id                 = aws_apigatewayv2_api.dashboard_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.location_api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "catch_all" {
  api_id    = aws_apigatewayv2_api.dashboard_api.id
  route_key = "GET /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.api_lambda.id}"
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.location_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.dashboard_api.execution_arn}/*/*"
}

# ===========================
# CloudWatch Alarms
# ===========================

resource "aws_cloudwatch_metric_alarm" "event_processor_errors" {
  alarm_name          = "${local.prefix}-event-processor-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Event processor Lambda errors exceeded threshold"

  dimensions = {
    FunctionName = aws_lambda_function.event_processor.function_name
  }
}

# ===========================
# Outputs
# ===========================

output "api_endpoint" {
  value = aws_apigatewayv2_api.dashboard_api.api_endpoint
}

output "iot_endpoint" {
  value = "Run: aws iot describe-endpoint --endpoint-type iot:Data-ATS"
}

output "locations_table" {
  value = aws_dynamodb_table.file_locations.name
}

output "movements_table" {
  value = aws_dynamodb_table.file_movements.name
}
