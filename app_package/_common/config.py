import os
from ws_config import ConfigWorkstation, ConfigDev, ConfigProd

match os.environ.get('WS_CONFIG_TYPE'):
    case 'dev':
        config = ConfigDev()
        print('- exFlaskBlueprintFrameworkStarterWithLogin/app_pacakge/config: Development')
    case 'prod':
        config = ConfigProd()
        print('- exFlaskBlueprintFrameworkStarterWithLogin/app_pacakge/config: Production')
    case _:
        config = ConfigWorkstation()
        print('- exFlaskBlueprintFrameworkStarterWithLogin/app_pacakge/config: Local')