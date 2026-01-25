param location string
param environmentName string
param backendImageTag string = 'latest'
param frontendImageTag string = 'latest'

@secure()
param postgresAdminPassword string = newGuid()

// Container Registry
resource acr 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' = {
  name: '${environmentName}acr${uniqueString(resourceGroup().id)}'
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// PostgreSQL Flexible Server
resource postgresqlServer 'Microsoft.DBforPostgreSQL/flexibleServers@2022-12-01' = {
  name: '${environmentName}-postgres-${uniqueString(resourceGroup().id)}'
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: 'adminuser'
    administratorLoginPassword: postgresAdminPassword
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

resource postgresqlDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2022-12-01' = {
  parent: postgresqlServer
  name: 'nycdb'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Firewall rule to allow Azure services
resource firewallRule 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2022-12-01' = {
  parent: postgresqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Storage Account for TLC Data
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: '${environmentName}data${uniqueString(resourceGroup().id)}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

// Blob Container for TLC Parquet Files
resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storageAccount.name}/default/tlc-data'
  properties: {
    publicAccess: 'None'
  }
}

// Container Apps Environment
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${environmentName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Log Analytics Workspace for Container Apps
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${environmentName}-logs-${uniqueString(resourceGroup().id)}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Container App Job for Data Loading
resource dataLoaderJob 'Microsoft.App/jobs@2023-05-01' = {
  name: '${environmentName}-data-loader-job'
  location: location
  properties: {
    environmentId: containerAppsEnvironment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 7200
      replicaRetryLimit: 0
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
        {
          name: 'database-url'
          value: 'postgresql://adminuser:${postgresAdminPassword}@${postgresqlServer.properties.fullyQualifiedDomainName}:5432/nycdb'
        }
        {
          name: 'storage-connection'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'data-loader'
          image: '${acr.properties.loginServer}/nyc-data-loader:latest'
          resources: {
            cpu: json('4.0')
            memory: '8Gi'
          }
          env: [
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection'
            }
          ]
        }
      ]
    }
  }
  dependsOn: [
    blobContainer
  ]
}

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: '${environmentName}-plan'
  location: location
  sku: {
    name: 'F1'
    tier: 'Free'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// Backend App Service
resource backendAppService 'Microsoft.Web/sites@2022-03-01' = {
  name: '${environmentName}-backend-${uniqueString(resourceGroup().id)}'
  location: location
  kind: 'app,linux,container'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|${acr.properties.loginServer}/backend:${backendImageTag}'
      appSettings: [
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: 'https://${acr.properties.loginServer}'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_USERNAME'
          value: acr.listCredentials().username
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_PASSWORD'
          value: acr.listCredentials().passwords[0].value
        }
        {
          name: 'DATABASE_URL'
          value: 'postgresql://adminuser:${postgresAdminPassword}@${postgresqlServer.properties.fullyQualifiedDomainName}:5432/nycdb'
        }
      ]
    }
  }
}

// Frontend App Service
resource frontendAppService 'Microsoft.Web/sites@2022-03-01' = {
  name: '${environmentName}-frontend-${uniqueString(resourceGroup().id)}'
  location: location
  kind: 'app,linux,container'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|${acr.properties.loginServer}/frontend:${frontendImageTag}'
      appSettings: [
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: 'https://${acr.properties.loginServer}'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_USERNAME'
          value: acr.listCredentials().username
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_PASSWORD'
          value: acr.listCredentials().passwords[0].value
        }
      ]
    }
  }
}

output containerRegistryLoginServer string = acr.properties.loginServer
output postgresqlServerName string = postgresqlServer.name
output appServiceName string = backendAppService.name
output frontendUrl string = frontendAppService.properties.defaultHostName
output backendUrl string = backendAppService.properties.defaultHostName
output storageAccountName string = storageAccount.name
output storageAccountKey string = storageAccount.listKeys().keys[0].value
output dataLoaderJobName string = dataLoaderJob.name
