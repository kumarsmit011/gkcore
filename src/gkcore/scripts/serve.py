from gkcore import BASE_DIR
import os, sys
from dotenv import load_dotenv

from subprocess import call

load_dotenv()

def main():
    """Wrapper around pserve to simplify environment selection.

    Usage: gkserve [--production | --development | <config_file>]

    production/development arguments will serve it in respective environment.
    Additionally custom environemnt configurations can be passed as an argument.
    """
    # Define default config file paths
    production_ini = os.path.join(BASE_DIR, "configs/production.ini")
    development_ini = os.path.join(BASE_DIR, "configs/development.ini")

    # Parse arguments
    ini_file = os.environ.get("PYRAMID_CONFIG_FILE")

    mode = "production"

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "--production":
            ini_file = production_ini
        elif arg == "--development":
            ini_file = development_ini
            mode = "development"
        elif arg.endswith(".ini"):  # Custom config file
            ini_file = arg
        else:
            print("Unknown argument:", arg)
            print("Usage: gkserve [--production | --development | <config_file>]")
            sys.exit(1)
    else:
        print("No argument provided. Defaulting to production.ini.")
        ini_file = production_ini

    # Ensure the selected ini file exists
    if not os.path.exists(ini_file):
        print(f"Error: Configuration file '{ini_file}' not found.")
        sys.exit(1)

    # Call Pyramid's pserve with the selected ini file
    print(f"Loading {ini_file}.")
    command = ["pserve", ini_file]
    if mode == "development":
        command.append("--reload")
    sys.exit(call(command))


if __name__ == "__main__":
    main()
