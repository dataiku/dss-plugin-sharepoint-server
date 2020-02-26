# SharePoint Server Plugin

This Dataiku DSS plugin provides a read / write connector to interact with documents stored on [SharePoint Server](https://products.office.com/sharepoint/sharepoint-server).

### Licence
This plugin is distributed under the Apache License version 2.0

## How to set up

- In DSS, go to **Plugins > Installed > SharePoint > Settings > SharePoint 2016 login**. There, fill in the details of the SharePoint instance you are trying to sync with DSS.
![Add a plugin preset](images/dss-sharepoint-2016-login.png)

## How to use

- In your DSS project flow, select **Dataset > SharePoint**
- Click **Shared Documents** or **Lists**, according to the data source you are trying to sync DSS to.
-  Pick the authentication type and the preset, and browse to the document or folder you want to use as dataset. If the source is a list, you will have know its name beforehand.
![Brose to dataset path](images/sharepoint-fs-dataset.png)
