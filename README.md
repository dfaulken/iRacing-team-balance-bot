# iRacing-team-balance-bot
Monitors the iRating of team members to find the optimal grouping of drivers into teams with balanced average iRating.

The goal of this exercise is to try and get as many teams from the same group as possible into a single split of an iRacing special event, so they can all race together.

## Setup

Add this bot to your server with [this link](https://discord.com/oauth2/authorize?client_id=803081668910383174&scope=bot&permissions=3072).
Once you've given the bot user the appropriate permissions in the channel that you'd like to use it in, talk to it by mentioning it.
For instance you might start with `@iRacing Team Balance Bot list commands` to see the list of available commands.

## Usage

1. Start by adding your drivers. You can do this by name, name and iRacing member ID, or just ID.
1. Set your team sizes for whatever event is upcoming. For instance, you might want to group your drivers into teams of 3 or teams of 4, but 5 would be too many and 2 would be too few.
1. You can now calculate the initial balance of drivers into teams (provided you have enough drivers for the team sizes you want). From here, you have a choice of whether you want to manually trigger a recheck of your drivers' iRatings and of the optimal balance, or whether you want it to occur automatically (currently, every 15 minutes).
   1. For manual rechecking: When you want to recheck, recheck everyone's iRating. Then recalculate the balance.
   1. For automatic rechecking: From the Discord channel to which you want the bot to send notifications, set the notification channel. The bot will then automatically recheck everyone's iRating and recalculate the balance.
1. As the event approaches, you may want to lock in your teams (for logistical reasons), but continue to be aware of how the balance of those teams is looking, regardless of whether it is the optimal balance or not. Set fixed teams in order to do this.
1. If you want to target a particular level of confidence that your teams will end up in the same split, set a balance threshold (e.g. 10). The bot will then keep track of where your current balance is relative to that threshold.

**From this point on, the information contained in this README is only for people who want to develop and deploy their own modified versions of this bot. If you just want to use the bot in your own Discord server, as it exists today, read no further.**

## Development

The code is (hopefully) structured in a relatively modular way, such that if you wanted to use just part of it, you could. For instance:

+ If you want the bot to do all of the same stuff, but you want to interact with it in a way that is not a Discord bot - maybe a Slack bot, maybe an SMS service, maybe just a CLI - just implement a new class that implements the basic `Interface` methods as seen in the DiscordChannel class.
+ If you want to just take the balancing logic and do something else with it, you should be able to just take the Balancer class and use it for whatever you want.
+ If you just want to do a better job of implementing the balancing algorithm but have the bot work exactly the same way, just replace the Balancer class with whatever you want, and then have the bot class use that instead.

## Setup

You'll need Python 3.8 or greater.

Install pip and use the requirements.txt to install dependencies.

Copy `.env.example` to `.env` and replace the example values with your actual bot client ID, and your actual iRacing username and password.

Run main.py and your bot should start up, sending its log output to `bot.log`.

## Testing

Run unit tests with
```
python -m unittest discover -s tests
```

## Deployment

I don't have formal automated deployment code (yet).

Personally, I deployed to an Ubuntu DigitalOcean droplet, and I use `supervisord` to start and stop the bot as a background service. If I need to push new code out, I stop the bot, do a manual `git pull`, and restart the bot. None of this is very good.

## Contributing

I welcome contributions of any kind. This project hasn't garnered enough interest yet to the point where I need formal rules for how to submit issues, pull requests, etc. If it does, I'll put them here.
