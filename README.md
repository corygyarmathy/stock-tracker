# stock-tracker

I am writing a stock tracker project in Python. This is a CLI tool to report on stock movement.

Stock Tracker - Installation and Usage Guide

## Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install stock-tracker
```

### Option 2: Install from source

```bash
git clone https://github.com/yourusername/stock-tracker.git 
cd stock-tracker
pip install .
```

## Configuration

Stock Tracker works out of the box with sensible defaults. You don't need to create any config files
to get started!
Default Configuration
The default configuration automatically:
• Creates a database in your current directory ( `stocktracker.db` )
• Reads CSV files from your current directory ( `import.csv` )
• Sets up logging with reasonable defaults

### Customising Configuration

There are two ways to customize the configuration:

#### Option 1: Custom Configuration File

Create a YAML configuration file with your preferred settings:

```yaml
# ~/.stock-tracker-config.yaml
db_path: ~/.stock--tracker/stocktracker.db
csv_path: ~/import.csv
log_file_path: ~/stock-tracker/logs/app.log
log_level: INFO
yf_max_requests: 2
yf_request_interval_seconds: 10
```

Then use it with the `--config-file` option:

```bash
stock-tracker --config-file ~/.stock-tracker-config.yaml report performance
```

Run `stock-tracker --help` to see all available options.

### Configuration Locations (Automatic Discovery)

If you don't specify a configuration file, Stock Tracker will look for configuration files in these locations (in order):

1. `./config/` (Current directory)
2. `~/.stock-tracker/config/` (User's home directory)
3. `/etc/stock-tracker/config/` (System-wide configuration)

The configuration files should be named:

- `config.base.yaml` - Base configuration
- `config.prod.yaml` - Production configuration

### Command-Line Options

Each configuration option can be overridden via command-line arguments:

```bash
stock-tracker --db-path ~/my-stocks.db --log-level DEBUG report performance
```

Available Commands
Import Stock Orders

```bash
stock-tracker import path/to/orders.csv
```

Refresh Stock Data

```bash
stock-tracker refresh prices
stock-tracker refresh dividends
stock-tracker refresh all
```

Generate Reports

```bash
stock-tracker report performance
stock-tracker report dividends
```

Interactive Mode

```bash
stock-tracker interactive
```

## CSV Format for Stock Orders

Your import CSV should have the following format:

```csv
datetime,exchange,ticker,quantity,price_paid,fee,note
2023-01-15 9:00:00,NASDAQ,AAPL,10,445.92,4.99,Initial purchase
```

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
