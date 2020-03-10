# SharePoint Server Plugin

This Dataiku DSS plugin provides a read / write connector to interact with documents stored on [SharePoint Server](https://products.office.com/sharepoint/sharepoint-server).

### Licence
This plugin is distributed under the Apache License version 2.0

## How to set up

- In DSS, go to **Plugins > Installed > SharePoint > Settings > SharePoint 2016 login**. There, fill in the details of the SharePoint instance you are trying to sync with DSS.
![Add a plugin preset](images/dss-sharepoint-2016-login.png)

Say a typical URL for files you want to give access to is `https://sharepoint.dataiku.com/sites/rnd/plugins/Shared%20Documents/safe/list.xlsx`

- **Host** is the scheme and the host name of your SharePoint server, here `https://sharepoint.dataiku.com`
- **Site path** is the path to the SharePoint site or subsite you want to give access to. In this example it would be `sites/rnd/plugins`
- **Root directory** is the path to the highest level directory you want your DSS users to have access to. In the current example, `Shared Documents/safe` will let the user browse any files and folders in the sub-directory `safe`. Default value for **Root directory** is `Shared Documents`, but it can also be left blank, in which case the user can access all the document libraries of the `rnd/plugins` site.

## How to use

- In your DSS project flow, select **Dataset > SharePoint**
- Click **Shared Documents** or **Lists**, according to the data source you are trying to sync DSS to.
-  Pick the authentication type and the preset, and browse to the document or folder you want to use as dataset. If the source is a list, you will have know its name beforehand.
![Browse to dataset path](images/sharepoint-fs-dataset.png)
