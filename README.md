# bird-config-generator

I'm not good at naming things, so it's exactly what it sounds like.

## Requirements
python3 and some modules:

`pip3 install jinja2 ipaddress jsonschema`

## Usage
Put your BGP session data in a json file (like `example.json`), run `python3 generate.py`, and it will either print an error or create BIRD config files in the local directory.

If you want to run the generator from somewhere else, you can specify the paths of the files it needs with CLI arguments:
```
usage: generate.py [-h] --config CONFIG --template TEMPLATE --schema SCHEMA
                   --outputFolder OUTPUTFOLDER

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG       json file with information used to generate router
                        config
  --template TEMPLATE   jinja2 template providing the config structure
  --schema SCHEMA       json schema used to validate the config file
  --outputFolder OUTPUTFOLDER
                        folder where generated files go
```

## Validation
Validation is done in two parts. First, it checks the config file against the schema for basic things (e.g. "is this field the right data type?"). Then it checks more complex rules (e.g. "is at least one of ipv4,ipv6 defined?"). If either step fails, it will print a descriptive error and exit. No files will be created.
