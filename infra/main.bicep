@description('Location for all resources.')
param location string = resourceGroup().location

@description('Unique environment prefix for Skylark Drones Blindfold BI')
param appName string = 'skylark-blindfold-bi'

@description('NVIDIA NIM API Key for free Llama-3.3-70B model inference')
@secure()
param nvidiaApiKey string = ''

@description('Container image tag for backend API')
param containerImageTag string = 'latest'

// Resource Names
var logAnalyticsName = '${appName}-logs'
var containerRegistryName = replace('${appName}cr', '-', '')
var containerAppEnvName = '${appName}-cae'
var backendAppName = '${appName}-api'
var staticWebAppName = '${appName}-frontend'

// 1. Log Analytics Workspace for Observability
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// 2. Azure Container Registry (Basic SKU)
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: containerRegistryName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// 3. Azure Container Apps Managed Environment
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKeyValue
      }
    }
  }
}

// 4. Azure Container App: Backend FastAPI + DuckDB Engine
resource backendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: backendAppName
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'OPTIONS']
          allowedHeaders: ['*']
        }
      }
      secrets: [
        {
          name: 'nvidia-api-key'
          value: nvidiaApiKey
        }
        {
          name: 'acr-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
      ]
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: '${containerRegistry.properties.loginServer}/skylark-backend:${containerImageTag}'
          resources: {
            cpu: json('1.0')
            memory: '2.0Gi'
          }
          env: [
            {
              name: 'NVIDIA_API_KEY'
              secretRef: 'nvidia-api-key'
            }
            {
              name: 'NVIDIA_BASE_URL'
              value: 'https://integrate.api.nvidia.com/v1'
            }
            {
              name: 'NVIDIA_MODEL'
              value: 'meta/llama-3.3-70b-instruct'
            }
            {
              name: 'APP_NAME'
              value: 'Blindfold BI - Skylark Drones'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// 5. Azure Static Web Apps: Vite + React 19 Frontend
resource staticWebApp 'Microsoft.Web/staticSites@2022-09-01' = {
  name: staticWebAppName
  location: 'eastus2' // Static web apps global deployment location
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    allowConfigFileUpdates: true
    stagingEnvironmentPolicy: 'Enabled'
  }
}

// Outputs
output acrLoginServer string = containerRegistry.properties.loginServer
output backendFqdn string = backendApp.properties.configuration.ingress.fqdn
output frontendDefaultHostname string = staticWebApp.properties.defaultHostname
