## CrossArk Scraper

Scrapes public servers for play count stats and posts it into Discord.

# Quickstart:

1. Add webhooks to the target discord channels
2. Edit scrape.py to update the correct path to endpoints.json
3. Edit endpoints.json to put the correct webhook URLs in
4. In your server config, add a cron job to run at '* * * * *' (ie, every minute) to run 'python /path/to/scrape.py'

Please note that only changes are posted.
