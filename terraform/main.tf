terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
    random  = { source = "hashicorp/random",  version = "~> 3.6" }
  }
}

provider "azurerm" {
  features {}
}

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
variable "location" {
  description = "Azure region to deploy into."
  type        = string
  default     = "eastus"
}

variable "project" {
  description = "Short name used to prefix resources."
  type        = string
  default     = "helpdesk"
}

# App configuration. Provide these in terraform.tfvars (git-ignored).
variable "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint URL."
  type        = string
}
variable "azure_openai_api_key" {
  description = "Azure OpenAI API key."
  type        = string
  sensitive   = true
}
variable "azure_search_endpoint" {
  description = "Azure AI Search endpoint URL."
  type        = string
}
variable "azure_search_api_key" {
  description = "Azure AI Search API key."
  type        = string
  sensitive   = true
}
variable "azure_search_index" {
  description = "Azure AI Search index name."
  type        = string
}

# ---------------------------------------------------------------------------
# Foundation
# ---------------------------------------------------------------------------
resource "random_string" "suffix" {
  length  = 5
  special = false
  upper   = false
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.project}"
  location = var.location
}

resource "azurerm_container_registry" "acr" {
  name                = "acr${var.project}${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true
}

resource "azurerm_log_analytics_workspace" "logs" {
  name                = "log-${var.project}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "env" {
  name                       = "cae-${var.project}"
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
}

# ---------------------------------------------------------------------------
# The app
# ---------------------------------------------------------------------------
resource "azurerm_container_app" "app" {
  name                         = "ca-${var.project}"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }
  secret {
    name  = "openai-api-key"
    value = var.azure_openai_api_key
  }
  secret {
    name  = "search-api-key"
    value = var.azure_search_api_key
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "helpdesk"
      image  = "${azurerm_container_registry.acr.login_server}/helpdesk:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = var.azure_openai_endpoint
      }
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "openai-api-key"
      }
      env {
        name  = "AZURE_SEARCH_ENDPOINT"
        value = var.azure_search_endpoint
      }
      env {
        name        = "AZURE_SEARCH_API_KEY"
        secret_name = "search-api-key"
      }
      env {
        name  = "AZURE_SEARCH_INDEX"
        value = var.azure_search_index
      }
    }
  }

  # The CI/CD pipeline updates the running image, so Terraform ignores it
  # to avoid reverting the deployed version on the next apply.
  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
output "acr_login_server"          { value = azurerm_container_registry.acr.login_server }
output "acr_name"                  { value = azurerm_container_registry.acr.name }
output "resource_group"            { value = azurerm_resource_group.rg.name }
output "container_app_environment" { value = azurerm_container_app_environment.env.name }
output "app_url"                   { value = "https://${azurerm_container_app.app.ingress[0].fqdn}" }
