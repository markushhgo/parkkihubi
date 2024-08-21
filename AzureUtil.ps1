$resourceGroup = "turku-dev-parkkihub39"

$parameters = ((az bicep build-params -f .\template.bicepparam --stdout 2>$nul | ConvertFrom-Json).parametersJson | ConvertFrom-Json).parameters

function Get-FromParameters($key) {
    return $parameters.$key.value
}

$registry = Get-FromParameters containerRegistryName
$apiImageName = Get-FromParameters apiImageName
$tileserverImageName = Get-FromParameters tileserverImageName
$uiImageName = Get-FromParameters uiImageName
$apiWebAppName = Get-FromParameters apiWebAppName
$tileserverWebAppName = Get-FromParameters tileserverWebAppName
$uiWebAppName = Get-FromParameters uiWebAppName
$db = Get-FromParameters dbServerName
$dbAdminUser = Get-FromParameters dbAdminUsername
$dbUser = Get-FromParameters dbUsername
$dbDatabase = Get-FromParameters dbName
$storage = Get-FromParameters storageAccountName
$sshPort = 59123

function Test-NetConnectionFaster($Addr, [int] $Port) {
    $TCPClient = [System.Net.Sockets.TcpClient]::new()
    $result = $TCPClient.ConnectAsync($Addr, $Port).Wait(100)
    $TCPClient.Close()
    return $result
}
function Open-AzureWebAppSshConnection($webApp) {
    $command = "az webapp create-remote-connection --resource-group $resourceGroup --name $webApp -p $sshPort"
    $job = Start-Job -ScriptBlock { Invoke-Expression $using:command }
    return $job.Id
}
function Test-AzureWebAppSshConnection {
    return Test-NetConnectionFaster 127.0.0.1 $sshPort
}
function Open-AzureWebAppSsh($webApp) {
    "Connecting to Azure WebApp... if this stalls, might need to run 'AzureUtil config ENABLE_SSH=true'"
    $jobId = Open-AzureWebAppSshConnection $webApp
    ssh-keygen -R [localhost]:$sshPort >nul 2>&1
    do {
        Start-Sleep -Milliseconds 10
    } until (Test-AzureWebAppSshConnection)
    "Connected, establishing SSH terminal. The password is 'Docker!'"
    ssh root@localhost -p $sshPort -o StrictHostKeyChecking=no
    Stop-Job $jobId
}

function Enable-PublicAccessToDb($enabled) {
    $myIp = Invoke-RestMethod https://api.ipify.org
    $firewallRuleName = "Temporary_$($myIp -replace '\.', '_')"
    if ($enabled) {
        "Enabling public network access to db..."
        az postgres flexible-server update --resource-group $resourceGroup --name $db --set network.publicNetworkAccess=Enabled >$nul
        "Whitelisting current IP in db networking..."
        az postgres flexible-server firewall-rule create --resource-group $resourceGroup --name $db -r $firewallRuleName --start-ip-address $myIp
    }
    else {
        "Removing current IP whitelisting from db networking..."
        az postgres flexible-server firewall-rule delete --resource-group $resourceGroup --name $db -r $firewallRuleName -y
        "Disabling public network access to db..."
        az postgres flexible-server update --resource-group $resourceGroup --name $db --set network.publicNetworkAccess=Disabled >$nul
    }
}

function Enable-PublicAccessToStorage($enabled) {
    $myIp = Invoke-RestMethod https://api.ipify.org
    if ($enabled) {
        if (-not (Test-AzureStorageConnection)) {
            "Enabling public network access to storage..."
            az storage account update -n $storage -g $resourceGroup --public-network-access Enabled --default-action Deny >$nul
            "Whitelisting current IP in storage networking..."
            az storage account network-rule add -n $storage -g $resourceGroup --ip-address $myIp >$nul
            do {
                Start-Sleep -Milliseconds 10
            } until (Test-AzureStorageConnection)
        }
    }
    else {
        "Removing current IP whitelisting from storage networking..."
        az storage account network-rule remove -n $storage -g $resourceGroup --ip-address $myIp >$nul
        "Disabling public network access to storage..."
        az storage account update -n $storage -g $resourceGroup --public-network-access Disabled >$nul
    }
}

function Enable-PublicAccessToRegistry($enabled) {
    $myIp = Invoke-RestMethod https://api.ipify.org
    if ($enabled) {
        "Enabling public network access to registry..."
        az acr update -n $registry -g $resourceGroup --public-network-enabled true --default-action Deny >$nul
        "Whitelisting current IP in registry networking..."
        az acr network-rule add -n $registry --resource-group $resourceGroup --ip-address $myIp >$nul
        az acr network-rule add -n $registry --resource-group $resourceGroup --ip-address 51.12.32.6 >$nul
        az acr network-rule add -n $registry --resource-group $resourceGroup --ip-address 51.12.32.7 >$nul
    }
    else {
        "Removing current IP whitelisting from registry networking..."
        az acr network-rule remove -n $registry --resource-group $resourceGroup --ip-address 51.12.32.7 >$nul
        az acr network-rule remove -n $registry --resource-group $resourceGroup --ip-address 51.12.32.6 >$nul
        az acr network-rule remove -n $registry --resource-group $resourceGroup --ip-address $myIp >$nul
        "Disabling public network access to registry..."
        az acr update -n $registry -g $resourceGroup --public-network-enabled false >$nul
    }
}

function Test-AzureStorageConnection {
    $myIp = Invoke-RestMethod https://api.ipify.org
    $isPublicAccessAllowed = (az storage account show -n $storage --query "publicNetworkAccess" --resource-group $resourceGroup -o tsv) -eq 'Enabled'
    $isMyIpAllowed = (az storage account show -n $storage --query "networkRuleSet.ipRules[?ipAddressOrRange=='$myIp']" --resource-group $resourceGroup).Length -gt 0
    return $isPublicAccessAllowed -and $isMyIpAllowed
}

function Open-AzurePostgresDb {
    Enable-PublicAccessToDb $true
    "Connecting to db..."
    psql -h "$db.postgres.database.azure.com" -U $dbUser -d $dbDatabase
    Enable-PublicAccessToDb $false
    "Done"
}

function Import-AzurePostgresDbDump($dumpFile) {
    Enable-PublicAccessToDb $true
    "Importing db dump..."
    $dbPassword = (Read-Host "Enter db user password" -MaskInput)
    psql -h "$db.postgres.database.azure.com" -U $dbAdminUser -d $dbDatabase -c "CREATE USER $dbUser WITH ENCRYPTED PASSWORD '$dbPassword'; ALTER USER $dbUser CREATEDB; GRANT $dbUser TO $dbAdminUser; GRANT ALL ON SCHEMA public TO $dbUser;"
    psql -h "$db.postgres.database.azure.com" -U $dbAdminUser -d $dbDatabase -f $dumpFile
    Enable-PublicAccessToDb $false
    "Done"
}

function Show-FilesInFileshare($fileshare, $path) {
    Enable-PublicAccessToStorage $true
    if ($path) {
        az storage file list --share-name $fileshare --account-name $storage --query [*].name --account-key (az storage account keys list -g $resourceGroup -n $storage --query [0].value) --path $path
    }
    else {
        az storage file list --share-name $fileshare --account-name $storage --query [*].name --account-key (az storage account keys list -g $resourceGroup -n $storage --query [0].value)
    }
    Enable-PublicAccessToStorage $false
}

function Copy-FilesToFileshare($fileshare, $paths) {
    Enable-PublicAccessToStorage $true
    Start-Sleep 20
    foreach ($path in $paths) {
        if ($path -match "=") {
            $parts = $path -split "="
            $source = $parts[0]
            $dest = $parts[1]
        }
        else {
            $source = $path
            $dest = ""
        }
        az storage copy -s $source -d https://$storage.file.core.windows.net/$fileshare/$dest --recursive --account-key (az storage account keys list -g $resourceGroup -n $storage --query [0].value)
    }
    Enable-PublicAccessToStorage $false
}

function Show-AzureWebAppLog($webApp) {
    az webapp log tail --resource-group $resourceGroup --name $webApp
}

function Invoke-AzureWebAppConfig($webApp, $commandOrConfigs) {
    if ($null -eq $commandOrConfigs) {
        az webapp config appsettings list --resource-group $resourceGroup --name $webApp | ConvertFrom-Json | Sort-Object -Property name | ForEach-Object { "$($_.name)=$($_.value)" }
    }
    elseif ($commandOrConfigs[0] -eq "delete") {
        az webapp config appsettings delete --resource-group $resourceGroup --name $webApp --setting-names ($commandOrConfigs | Select-Object -Skip 1)
    }
    else {
        az webapp config appsettings set --resource-group $resourceGroup --name $webApp --settings $commandOrConfigs
    }
}

function Invoke-BuildAzureContainerImage($image, $path = ".") {
    Enable-PublicAccessToRegistry $true
    az acr build --resource-group $resourceGroup --registry $registry --image $image $path
    Enable-PublicAccessToRegistry $false
}

function Invoke-ImportAzureContainerImage($image, $source) {
    az acr import --resource-group $resourceGroup --name $registry --source $source --image $image
}

function Get-WebAppName($webApp) {
    switch ($webApp) {
        "api" { $apiWebAppName }
        "tileserver" { $tileserverWebAppName }
        "ui" { $uiWebAppName }
        Default { $null }
    }
}

function Get-ImageName($webApp) {
    switch ($webApp) {
        "api" { $apiImageName }
        "tileserver" { $tileserverImageName }
        "ui" { $uiImageName }
        Default { $null }
    }
}

function Get-WebAppFileshare($webApp) {
    switch ($webApp) {
        "api" { 'files' }
        Default { $null }
    }
}

function Show-Usage {
    "Usage:"
    ""
    "./AzureUtil deploy"
    "`tCreate a new resource group and deploy resources to it using template.bicep and parameters from parameters.json"
    "./AzureUtil build [api|tileserver|ui] [path]"
    "`tBuild a new image in the WebApp's Azure container registry"
    "./AzureUtil importimage [api|tileserver|ui] [docker.io/helsinki/tileserver-gl]"
    "`tImport an online image in the WebApp's Azure container registry"
    "./AzureUtil log [api|tileserver|ui]"
    "`tView the WebApp's log stream"
    "./AzureUtil ssh [api|tileserver|ui]"
    "`tAccess the WebApp's SSH, assuming one is set up in docker-entrypoint"
    "./AzureUtil db"
    "`tAccess Azure Postgres DB Flexible Server instance with psql"
    "./AzureUtil dbimport [dump.sql]"
    "`tImport a DB dump file to Azure Postgres DB Flexible Server instance with psql"
    "./AzureUtil config [api|tileserver|ui]"
    "`tShow the WebApp's environment variables in a .env file format"
    "./AzureUtil config [api|tileserver|ui] setting1=value1 setting2=value2 ..."
    "`tAssign the given values in the WebApp's environment variables"
    "./AzureUtil config delete [api|tileserver|ui] setting1 setting2 ..."
    "`tDelete the given keys from the WebApp's environment variables"
    "./AzureUtil files [apifiles|apidata|tileserver|ui] [path]"
    "`tList files in the Azure Storage fileshare using a path"
    "./AzureUtil copyfiles [apifiles|apidata|tileserver|ui] [d:/turku/remote/servicemap-test/bew/staticroot]"
    "`tCopy files to the Azure Storage fileshare"
    "./AzureUtil param [dbName]"
    "`tShow a config value from parameters.json"
}

switch ($args[0]) {
    "deploy" {
        az group create -l swedencentral -n $resourceGroup
        $dbAdminPassword = (Read-Host "Enter db admin password" -MaskInput)
        $dbPassword = (Read-Host "Enter db user password" -MaskInput)
        az deployment group create --template-file .\template.bicep --parameters 'template.bicepparam' --parameters dbAdminPassword=$dbAdminPassword dbPassword=$dbPassword --resource-group $resourceGroup
    }
    "build" {
        $imageName = Get-ImageName $args[1]
        if ($null -ne $imageName) {
            Invoke-BuildAzureContainerImage $imageName $args[2]
        }
        else { Show-Usage }
    }
    "importimage" {
        $imageName = Get-ImageName $args[1]
        if ($null -ne $imageName) {
            Invoke-ImportAzureContainerImage $imageName $args[2]
        }
        else { Show-Usage }
    }
    "log" {
        $webAppName = Get-WebAppName $args[1]
        if ($null -ne $webAppName) {
            Show-AzureWebAppLog $webAppName
        }
        else { Show-Usage }
    }
    "ssh" {
        $webAppName = Get-WebAppName $args[1]
        if ($null -ne $webAppName) {
            Open-AzureWebAppSsh $webAppName
        }
        else { Show-Usage }
    }
    "db" {
        Open-AzurePostgresDb
    }
    "dbimport" {
        Import-AzurePostgresDbDump $args[1]
    }
    "config" {
        $webAppName = Get-WebAppName $args[1]
        if ($null -ne $webAppName) {
            Invoke-AzureWebAppConfig $webAppName ($args | Select-Object -Skip 2)
        }
        else { Show-Usage }
    }
    "files" {
        $fileshare = Get-WebAppFileshare $args[1]
        if ($null -ne $fileshare) {
            Show-FilesInFileshare $fileshare $args[2]
        }
        else { Show-Usage }
    }
    "copyfiles" {
        $fileshare = Get-WebAppFileshare $args[1]
        if ($null -ne $fileshare) {
            Copy-FilesToFileshare $fileshare ($args | Select-Object -Skip 2)
        }
        else { Show-Usage }
    }
    "param" {
        Write-Output (Get-FromParameters $args[1])
    }
    Default {
        Show-Usage
    }
}