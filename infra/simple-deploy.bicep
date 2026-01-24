param location string = 'westus'
param environmentName string = 'nyc'

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

output containerRegistryName string = acr.name
output containerRegistryLoginServer string = acr.properties.loginServer
output resourceGroupName string = resourceGroup().name
