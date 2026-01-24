targetScope = 'subscription'

param location string = 'westus'
param environmentName string = 'nyc'
param resourceGroupName string = '${environmentName}-rg'

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
}

module resources 'resources.bicep' = {
  name: 'resources'
  scope: rg
  params: {
    location: location
    environmentName: environmentName
  }
}

output resourceGroupName string = rg.name
output containerRegistryLoginServer string = resources.outputs.containerRegistryLoginServer
output postgresqlServerName string = resources.outputs.postgresqlServerName
output appServiceName string = resources.outputs.appServiceName
