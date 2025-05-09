# stock-tracker

I am writing a stock tracker project in Python. This is a CLI tool to report on stock movement.

## Features

- CLI application
- Take a CSV with stock order data as input (this would include the datetime of purchase, exchange, stock-ticker, quantity, and price paid)
- Verify the orders are valid (can get info from yfinance for them)
- Store all verified stock orders into a sqlite database
- Get the current information of the stocks via API (using yfinance module)
- Calculate capital gains for each stock (by calculating the gains for each stock order) (and cumulatively in the portfolio)
- Calculate received dividends for each stock (by calculating the dividends for each stock order) (and cumulatively in the portfolio)
- Calculate total gains (capital gains + dividends)
- All calculations would take into account the different orders (there may be multiple orders for the same stock, with each one leading to a different return)
- Display information with ASCII charts
- Handle the following tricky scenarios:
  - Cross-exchange equivalents
  - Currency conversion and
  - Stock splitting
  - Mergers & acquisitions
  - Stock de-listing

## Dev Env / Config Management

I am constructing the dev environment, and managing the configuration with the following approach:

- dev env is set through direnv, which is only used to automatically load my nix shell when opening the project directory in the terminal.
- The Nix Shell environment is defined in flake.nix. This installs all the dependencies, applications, packages etc., sets up the Python virtual environment, and sets the required environment variables. (This is basically all the 'OS' stuff)
- python-dotenv is used to load data from the .env file as environment variables - I only use this to set the ENV environment variable (setting whether I'm running in test, dev, or prod environments).
- In my code I have the ConfigLoader class. This takes the ENV environment variable, and loads the appropriate config.{env}.yaml file. It then validates the inputs are correct according to what the AppConfig class is expecting.
  - The ConfigLoader class further supports CLI overriding of any of the parameters.
  - So the layered-config order goes env. variables -> config.base.yaml -> config.{env}.yaml -> CLI arguments
- The AppConfig class is a Python dataclass just holding the config of the app as class attributes. It has a private singleton object which holds this data, which is accessed through a get() method.
