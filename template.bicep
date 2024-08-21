param location string = resourceGroup().location
param apiImageName string
@description('API WebApp name. Must be globally unique')
param apiWebAppName string
@description('API Replica WebApp name. Must be globally unique')
param apiReplicaWebAppName string
@description('Cache name. Must be globally unique')
param cacheName string
param keyvaultName string
param serverfarmPlanName string
@description('Storage account name. Must be globally unique. Lowercase and numbers only')
@maxLength(24)
@minLength(3)
param storageAccountName string
param vnetName string
@description('Container registry name. Must be globally unique. Alphanumeric only')
@maxLength(50)
@minLength(5)
param containerRegistryName string
param dbServerName string
param dbServerReplicaName string
param dbName string
param workspaceName string
param appInsightsName string
param dbPostgresExtensions string = 'POSTGIS,HSTORE,PG_TRGM'
param dbAdminUsername string
param dbUsername string
@secure()
param dbAdminPassword string = ''
@secure()
param dbPassword string = ''
param apiUrl string

param apiAppSettings object = {
  ALLOWED_HOSTS: '${apiWebAppName}.azurewebsites.net,testiparkki.turku.fi,127.0.0.1,localhost'
  EMAIL_URL: 'smtp://smtp.turku.fi:25'
  ENABLE_SSH: 'true'
  MEDIA_ROOT: '/fileshare/mediaroot'
  MEDIA_URL: '/media/'
  RUN_MODE: 'production'
  SECRET_KEY: 'zvy1rFWcIa0TJauTOhh8hJFEAwxf0fy7jAoUZWGoNV6Nyc0zUHp2A6uSsat9'
  SENTRY_DSN: 'https://a370518c0c0c46c39a2705c91f738998@sentry.haltu.net/29'
  STATIC_ROOT: '/fileshare/staticroot'
  STATIC_URL: '/static/'
  TIER: 'prod'
  WEBSITE_HEALTHCHECK_MAXPINGFAILURES: '10'
  WEBSITE_HTTPLOGGING_RETENTION_DAYS: '3'
}

@allowed([
  0
  1
  2
  3
  4
  5
])
param cacheCapacity int = 1

var webAppRequirements = [
  {
    name: apiWebAppName
    image: apiImageName
    appSettings: union(apiAppSettings, {
      DATABASE_URL: '@Microsoft.KeyVault(VaultName=${keyvault.name};SecretName=${keyvault::dbUrlSecret.name})'
      CACHE_URL: '@Microsoft.KeyVault(VaultName=${keyvault.name};SecretName=${keyvault::cacheUrlSecret.name})'
    })
    fileshares: {
      files: '/fileshare'
    }
  }
  {
    name: apiReplicaWebAppName
    image: apiImageName
    appSettings: union(apiAppSettings, {
      DATABASE_URL: '@Microsoft.KeyVault(VaultName=${keyvault.name};SecretName=${keyvault::dbReplicaUrlSecret.name})'
      CACHE_URL: '@Microsoft.KeyVault(VaultName=${keyvault.name};SecretName=${keyvault::cacheReplicaUrlSecret.name})'
    })
    fileshares: {
      files: '/fileshare'
    }
  }
]

var fileshareNames = union(flatten(map(webAppRequirements, x => objectKeys(x.fileshares))), [])

var dnsZoneRequirements = [
  'privatelink.azurecr.io'
  'privatelink.file.core.windows.net'
  'privatelink.postgres.database.azure.com'
  'privatelink.redis.cache.windows.net'
  'privatelink.vaultcore.azure.net'
]

var subnetRequirements = [
  {
    name: 'default'
    delegations: []
    serviceEndpoints: []
  }
  {
    name: 'azureservices'
    delegations: []
    serviceEndpoints: []
  }
  {
    name: 'applicationgateway'
    delegations: []
    serviceEndpoints: []
  }
  {
    name: 'api'
    delegations: ['Microsoft.Web/serverfarms'] // Required
    serviceEndpoints: []
  }
]

var privateEndpointRequirements = [
  {
    name: '${cacheName}-endpoint'
    privateLinkServiceId: cache.id
    groupId: 'redisCache'
    privateDnsZoneName: 'privatelink.redis.cache.windows.net'
    privateDnsZoneId: dnsZone[3].id
  }
  {
    name: '${containerRegistryName}-endpoint'
    privateLinkServiceId: containerRegistry.id
    groupId: 'registry'
    privateDnsZoneName: 'privatelink.azurecr.io'
    privateDnsZoneId: dnsZone[0].id
  }
  {
    name: '${storageAccountName}-endpoint'
    privateLinkServiceId: storageAccount.id
    groupId: 'file'
    privateDnsZoneName: 'privatelink.file.core.windows.net'
    privateDnsZoneId: dnsZone[1].id
  }
  {
    name: '${keyvaultName}-endpoint'
    privatelinkServiceId: keyvault.id
    groupId: 'vault'
    privateDnsZoneName: 'privatelink.vaultcore.azure.net'
    privateDnsZoneId: dnsZone[4].id
  }
  {
    name: '${dbServerName}-endpoint'
    privateLinkServiceId: dbs[0].id
    groupId: 'postgresqlServer'
    privateDnsZoneName: 'privatelink.postgres.database.azure.com'
    privateDnsZoneId: dnsZone[2].id
  }
  {
    name: '${dbServerReplicaName}-endpoint'
    privateLinkServiceId: dbs[1].id
    groupId: 'postgresqlServer'
    privateDnsZoneName: 'privatelink.postgres.database.azure.com'
    privateDnsZoneId: dnsZone[2].id
  }
]

resource workspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: workspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    workspaceCapping: {}
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: ['10.0.0.0/16']
    }
    encryption: {
      enabled: false
      enforcement: 'AllowUnencrypted'
    }
    virtualNetworkPeerings: []
    enableDdosProtection: false
  }

  @batchSize(1)
  resource subnets 'subnets@2023-11-01' = [
    for i in range(0, length(subnetRequirements)): {
      name: subnetRequirements[i].name
      properties: {
        addressPrefixes: ['10.0.${i}.0/24']
        serviceEndpoints: [
          for serviceEndpoint in subnetRequirements[i].serviceEndpoints: {
            service: serviceEndpoint
            locations: [location]
          }
        ]
        delegations: [
          for delegation in subnetRequirements[i].delegations: {
            name: 'delegation'
            properties: {
              serviceName: delegation
            }
            type: 'Microsoft.Network/virtualNetworks/subnets/delegations'
          }
        ]
        privateEndpointNetworkPolicies: 'Disabled'
        privateLinkServiceNetworkPolicies: 'Enabled'
      }
    }
  ]
}

resource dnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = [
  for dnsZoneRequirement in dnsZoneRequirements: {
    name: dnsZoneRequirement
    location: 'global'
    properties: {}
  }
]

resource privateDnsZoneVnetLinks 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = [
  for i in range(0, length(dnsZoneRequirements)): {
    parent: dnsZone[i]
    location: 'global'
    name: 'vnetlink'
    properties: {
      registrationEnabled: false
      virtualNetwork: {
        id: vnet.id
      }
    }
  }
]

resource cache 'Microsoft.Cache/Redis@2024-04-01-preview' = {
  name: cacheName
  location: location
  properties: {
    redisVersion: '6.0'
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: cacheCapacity
    }
    enableNonSslPort: false
    publicNetworkAccess: 'Disabled'
    redisConfiguration: {
      'aad-enabled': 'true'
      'maxmemory-reserved': '30'
      'maxfragmentationmemory-reserved': '30'
      'maxmemory-delta': '30'
    }
    updateChannel: 'Stable'
    disableAccessKeyAuthentication: false
  }
  dependsOn: [
    dnsZone[3]
    vnet::subnets[1]
  ]
}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: containerRegistryName
  location: location
  sku: {
    name: 'Premium'
  }
  properties: {
    adminUserEnabled: true // Required to create RBAC rights
    publicNetworkAccess: 'Disabled'
  }
  dependsOn: [
    dnsZone[0]
    vnet::subnets[1]
  ]

  resource webhooks 'webhooks@2023-01-01-preview' = [
    for webAppRequirement in webAppRequirements: {
      name: '${replace(webAppRequirement.name, '-', '')}webhook'
      location: location
      properties: {
        actions: ['push']
        scope: '${webAppRequirement.image}:latest'
        serviceUri: '${list(resourceId('Microsoft.Web/sites/config', webAppRequirement.name, 'publishingcredentials'), '2015-08-01').properties.scmUri}/docker/hook'
        status: 'enabled'
      }
    }
  ]
}

resource dbs 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = [
  for isPrimary in [true, false]: {
    name: isPrimary ? dbServerName : dbServerReplicaName
    location: location
    sku: {
      //name: 'Standard_B1ms'
      //tier: 'Burstable' // TODO: must be above Burstable for replication
      name: 'Standard_D2ds_v5'
      tier: 'GeneralPurpose'
}
    properties: {
      //replicationRole: 'AsyncReplica'
      replica: {
        role: isPrimary ? 'Primary' : 'AsyncReplica'
      }
      sourceServerResourceId: isPrimary ? null : resourceId('Microsoft.DBforPostgreSQL/flexibleServers', dbServerName)
      storage: {
        iops: 120
        tier: 'P4'
        storageSizeGB: 32
        autoGrow: 'Disabled'
      }
      network: {
        publicNetworkAccess: 'Disabled'
      }
      dataEncryption: {
        type: 'SystemManaged'
      }
      authConfig: {
        activeDirectoryAuth: 'Disabled'
        passwordAuth: 'Enabled'
      }
      version: '16'
      administratorLogin: dbAdminUsername
      administratorLoginPassword: dbAdminPassword
      availabilityZone: '2'
    }
    dependsOn: isPrimary
      ? [
          dnsZone[2]
          vnet::subnets[1]
        ]
      : [
          dnsZone[2]
          vnet::subnets[1]
          resourceId('Microsoft.DBforPostgreSQL/flexibleServers', dbServerName)
        ]
  }
]

resource dbConfigurationClientEncoding 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-12-01-preview' = {
  name: 'client_encoding'
  parent: dbs[0]
  properties: {
    value: 'UTF8'
    source: 'user-override'
  }
  dependsOn: [waitForDbReady]
}

resource dbConfigurationAzureExtensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-12-01-preview' = {
  name: 'azure.extensions'
  parent: dbs[0]
  properties: {
    value: dbPostgresExtensions
    source: 'user-override'
  }
  dependsOn: [waitForDbReady]
}

resource dbDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  name: dbName
  parent: dbs[0]
  properties: {
    charset: 'UTF8'
    collation: 'fi_FI.utf8'
  }
}

resource waitForDbReady 'Microsoft.Resources/deploymentScripts@2023-08-01' = {
  kind: 'AzurePowerShell'
  name: 'waitForDbReady'
  location: location
  properties: {
    azPowerShellVersion: '3.0'
    scriptContent: 'start-sleep -Seconds 300'
    cleanupPreference: 'Always'
    retentionInterval: 'PT1H'
  }
  dependsOn: [dbs[0]]
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    dnsEndpointType: 'Standard'
    publicNetworkAccess: 'Disabled'
    allowSharedKeyAccess: true // Required for uploading files with Azure CLI
    largeFileSharesState: 'Enabled'
    networkAcls: {
      bypass: 'AzureServices' // TODO: try remove
      defaultAction: 'Deny'
    }
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot' // Required since swedencentral doesn't support others at the time of writing, even if we don't use blob storage
  }

  resource fileServices 'fileServices@2024-01-01' = {
    name: 'default'

    resource fileshares 'shares@2024-01-01' = [
      for fileshareName in fileshareNames: {
        name: fileshareName
      }
    ]
  }
}

resource serverfarmPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: serverfarmPlanName
  location: location
  sku: {
    name: 'P0v3'
    tier: 'Premium0V3'
    size: 'P0v3'
    family: 'Pv3'
    capacity: 1
  }
  kind: 'linux'
  properties: {
    perSiteScaling: false
    elasticScaleEnabled: false
    maximumElasticWorkerCount: 1
    isSpot: false
    reserved: true
    isXenon: false
    hyperV: false
    targetWorkerCount: 0
    targetWorkerSizeId: 0
    zoneRedundant: false
  }
}

resource privateEndpoints 'Microsoft.Network/privateEndpoints@2023-11-01' = [
  for privateEndpointRequirement in privateEndpointRequirements: {
    name: privateEndpointRequirement.name
    location: location
    properties: {
      privateLinkServiceConnections: [
        {
          name: privateEndpointRequirement.name
          properties: {
            privateLinkServiceId: privateEndpointRequirement.privateLinkServiceId
            groupIds: [privateEndpointRequirement.groupId]
          }
        }
      ]
      customNetworkInterfaceName: '${privateEndpointRequirement.name}-nic'
      subnet: {
        id: vnet::subnets[1].id
      }
    }
  }
]

resource privateDnsZoneGroups 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = [
  for i in range(0, length(privateEndpointRequirements)): {
    parent: privateEndpoints[i]
    name: 'default'
    properties: {
      privateDnsZoneConfigs: [
        {
          name: privateEndpointRequirements[i].privateDnsZoneName
          properties: {
            privateDnsZoneId: privateEndpointRequirements[i].privateDnsZoneId
          }
        }
      ]
    }
  }
]

resource webApps 'Microsoft.Web/sites@2023-12-01' = [
  for webAppRequirement in webAppRequirements: {
    name: webAppRequirement.name
    location: location
    kind: 'app,linux,container'
    identity: {
      type: 'SystemAssigned'
    }
    properties: {
      serverFarmId: serverfarmPlan.id
      reserved: true
      isXenon: false
      hyperV: false
      dnsConfiguration: {}
      vnetRouteAllEnabled: true
      vnetImagePullEnabled: true
      vnetContentShareEnabled: false
      siteConfig: {
        numberOfWorkers: 1
        linuxFxVersion: 'DOCKER|${containerRegistryName}.azurecr.io/${webAppRequirement.image}:latest'
        acrUseManagedIdentityCreds: true
        alwaysOn: true
        http20Enabled: false
        functionAppScaleLimit: 0
        minimumElasticInstanceCount: 1
        azureStorageAccounts: reduce(
          items(webAppRequirement.fileshares),
          {},
          (build, fileshare) =>
            union(build, {
              '${fileshare.key}-mount': {
                type: 'AzureFiles'
                accountName: storageAccountName
                shareName: fileshare.key
                mountPath: fileshare.value
                protocol: 'Smb'
                accessKey: listKeys(
                  resourceId('Microsoft.Storage/storageAccounts', storageAccountName),
                  providers('Microsoft.Storage', 'storageAccounts').apiVersions[0]
                ).keys[0].value
              }
            })
        )
        ipSecurityRestrictions: [
          {
            ipAddress: 'Any'
            action: 'Allow'
            priority: 2147483647
            name: 'Allow all'
            description: 'Allow all access'
          }
        ]
        scmIpSecurityRestrictions: [
          {
            ipAddress: 'Any'
            action: 'Allow'
            priority: 2147483647
            name: 'Allow all'
            description: 'Allow all access'
          }
        ]
        appSettings: map(
          items(union(webAppRequirement.appSettings, {
            DOCKER_ENABLE_CI: 'true'
            APPLICATIONINSIGHTS_CONNECTION_STRING: appInsights.properties.ConnectionString
            ApplicationInsightsAgent_EXTENSION_VERSION: '~3'
            XDT_MicrosoftApplicationInsights_Mode: 'Recommended'
          })),
          x => {
            name: x.key
            value: x.value
          }
        )
      }
      scmSiteAlsoStopped: false
      clientAffinityEnabled: false
      clientCertEnabled: false
      clientCertMode: 'Required'
      hostNamesDisabled: false
      vnetBackupRestoreEnabled: false
      customDomainVerificationId: 'B12052C74774A58FE9AA188A3D712ADE96EB2FE1F40FF5FC31E7A8B9AF742255'
      containerSize: 0
      dailyMemoryTimeQuota: 0
      httpsOnly: true
      redundancyMode: 'None'
      publicNetworkAccess: 'Enabled'
      storageAccountRequired: false
      virtualNetworkSubnetId: vnet::subnets[3].id
      keyVaultReferenceIdentity: 'SystemAssigned'
    }
  }
]

resource keyvault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyvaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enabledForDeployment: true
    enabledForDiskEncryption: true
    enabledForTemplateDeployment: true
    enableRbacAuthorization: true
    publicNetworkAccess: 'Disabled'
  }

  resource dbUrlSecret 'secrets' = {
    name: 'dbUrl'
    properties: {
      value: 'postgis://${dbUsername}:${dbPassword}@${dbServerName}.postgres.database.azure.com/${dbName}'
    }
  }

  resource dbReplicaUrlSecret 'secrets' = {
    name: 'dbReplicaUrl'
    properties: {
      value: 'postgis://${dbUsername}:${dbPassword}@${dbServerReplicaName}.postgres.database.azure.com/${dbName}'
    }
  }

  resource cacheUrlSecret 'secrets' = {
    name: 'cacheUrl'
    properties: {
      value: 'rediss://:${cache.listKeys().primaryKey}@${cacheName}.redis.cache.windows.net:6380/0'
    }
  }

  resource cacheReplicaUrlSecret 'secrets' = {
    name: 'cacheReplicaUrl'
    properties: {
      value: 'rediss://:${cache.listKeys().primaryKey}@${cacheName}.redis.cache.windows.net:6380/1'
    }
  }
}

@description('Key Vault Secret User role')
resource keyVaultSecretUserRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '4633458b-17de-408a-b874-0445c86b69e6'
}

@description('Container Registry AcrPull role')
resource acrPullRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '7f951dda-4ed3-4680-a7ca-43fe172d538d'
}

@description('Grant the app service identity with key vault secret user role permissions over the key vault. This allows reading secret contents')
resource webAppKeyvaultSecretUserRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for i in range(0, length(webAppRequirements)): {
  scope: keyvault
  name: guid(resourceGroup().id, webApps[i].id, keyVaultSecretUserRoleDefinition.id)
  properties: {
    roleDefinitionId: keyVaultSecretUserRoleDefinition.id
    principalId: webApps[i].identity.principalId
    principalType: 'ServicePrincipal'
  }
}]

@description('Grant the app service identity with ACR pull role permissions over the container registry. This allows pulling container images')
resource webAppAcrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: containerRegistry
  name: guid(resourceGroup().id, webApps[0].id, acrPullRoleDefinition.id)
  properties: {
    roleDefinitionId: acrPullRoleDefinition.id
    principalId: webApps[0].identity.principalId
    principalType: 'ServicePrincipal'
  }
}
