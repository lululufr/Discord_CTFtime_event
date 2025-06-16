# Bot discord CTFtime Team event manager

Allow to manage and subscribe to CTFtime event with your team. 


Image : 
TODO


In order to launch the bot : 
```bash

cp .env.example .env
# Fill the .env file with your discord bot token and CTFtime team id

poetry install 
poetry run python -m src.discord_ctftime.bot.main

```

Docker compose is not yet done.