
# What Sticks 13 API

![What Sticks Logo](https://what-sticks.com/website_images/wsLogo180.png)

## Description
What Sticks 13 API is the main conduit for the What Sticks iOS application to communicate with the What Sticks Database.
This project picks up from the WhatSticks13Api migrate_to_mysql_04 branch.

## Features
- Users can register
- Users can submit data from Apple Health and other iPhone related data to populate their dashboards in the WSiOS application.


## Contributing
We welcome contributions to the WhatSticks13 API project.

For any queries or suggestions, please contact us at nrodrig1@gmail.com.


## Documentation

### ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT
ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT is a variable in ws_config/config.py. If it is set to `True`, it will stop WhatSticks13Api from logging in and registering users. Furthermore, it provides alert_title and alert_message sent by the WS11Api that the WSiOS app will display to the user conveying the technical difficulty. The mechanisim this works through is a function in WS11Api/utilsDecorators.py.

If it is set to anything except for `True`, it will allow the normal logging in and registering function.


## Project Folder Structure
```
.
├── README.md
├── app_package
│   ├── __init__.py
│   ├── _common
│   │   ├── config.py
│   │   ├── token_decorator.py
│   │   └── utilities.py
│   ├── bp_apple_health
│   │   ├── routes.py
│   │   └── utils.py
│   ├── bp_errors
│   │   └── routes.py
│   └── bp_users
│       ├── routes.py
│       └── utils.py
├── docs
│   └── images
│       └── wsLogo_200px.png
├── requirements.txt
└── run.py
```
