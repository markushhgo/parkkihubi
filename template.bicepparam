using 'template.bicep'

var prefix = readEnvironmentVariable('RESOURCE_PREFIX')
var sanitizedPrefix = replace(prefix, '-', '')
param apiImageName = 'api'
param apiUrl = 'https://parkki-testi.turku.fi'
param apiWebAppName = '${prefix}-api'
param apiReplicaUrl = 'https://parkkiopas-testi.turku.fi'
param apiReplicaWebAppName = '${prefix}-replica-api'
param appInsightsName = '${prefix}-appinsights'
param cacheName = '${prefix}-cache'
param containerRegistryName = '${sanitizedPrefix}registry'
param dbName = 'parkkihub'
param dbServerName = '${prefix}-db'
param dbServerReplicaName = '${prefix}-replica-db'
param dbAdminUsername = 'turkuadmin'
param dbUsername = 'parkkihub_testi'
param keyvaultName = '${sanitizedPrefix}-kv'
param serverfarmPlanName = 'serviceplan'
param storageAccountName = '${sanitizedPrefix}store'
param apiOutboundIpName = 'turku-test-parkkihub-outbound-ip'
param natGatewayName = '${prefix}-nat'
param vnetName =  '${prefix}-vnet'
param workspaceName = '${prefix}-workspace'
