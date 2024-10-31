# Aruba Find Rogues Script

This script will pull the rogue data from Aruba Central. Check the SSIDs against the list of ssids in the `check_ssids` variable. A print a Rogue Report. This report can be saved or emailed as HTML.

Copy the `env.yaml.sample` to `.env.yaml`
Edit the `.env.yaml` file with your Aruba Central API keys, SendGrid API, and your central login account.

The SendGrid API key is only necessary if you want to email the report to users.

Central Account Login is only needed if you want the script to create refresh and access tokens.

Docker commands should work...

```

./build.sh

docker run --rm -it find_rogues

```
