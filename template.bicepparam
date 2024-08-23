using 'template.bicep'

var prefix = readEnvironmentVariable('RESOURCE_PREFIX')
var sanitizedPrefix = replace(prefix, '-', '')
param apiImageName = 'api'
param apiUrl =  'https://${prefix}-api.azurewebsites.net'
param apiWebAppName =  '${prefix}-api'
param apiReplicaWebAppName =  '${prefix}-replica-api'
param appInsightsName =  '${prefix}-appinsights'
param cacheName =  '${prefix}-cache'
param containerRegistryName =  '${sanitizedPrefix}registry'
param dbName =  'parkkihub'
param dbServerName =  '${prefix}-db'
param dbServerReplicaName =  '${prefix}-replica-db'
param dbAdminUsername =  'turkuadmin'
param dbUsername =  'parkkihub_testi'
param keyvaultName =  '${prefix}-kv'
param serverfarmPlanName =  'serviceplan'
param storageAccountName =  '${sanitizedPrefix}store'
param vnetName =  'vnet'
param workspaceName = '${prefix}-workspace'
