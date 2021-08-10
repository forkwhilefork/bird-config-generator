# bird-config-generator

A utility for generating a valid configuration file for the [bird](https://bird.network.cz/) routing daemon from a json config file.

## ⚠ Disclaimer ⚠
This tool is not production-ready. It doesn't even have a real name. Use it at your own risk. (But if you do use it, please let me know how it goes!)

## Requirements
python3 and some modules:

`pip3 install jinja2 ipaddress difflib jsonschema wasabi`

A working installation of bird2 (excluding config) is assumed.

## Usage
Put your routing configuration data in a json file (like `example.json`) and run `python3 generate.py`. The tool will parse the config file, generate an output, and depending on the mode of operation, it may write it to a file. For more details on the modes of operation, see [Modes of Operation](#modes-of-operation).

To override the default mode or set the input/output locations, use the CLI argument as specified below:
```
usage: generate.py [-h] --config CONFIG --outputPath OUTPUTPATH
                   [--mode {dryrun,prompt,overwrite}]

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG       json file with information used to generate router
                        config (default 'config.json')
  --outputPath OUTPUTPATH
                        path of generated file (default '.')
  --mode {dryrun,prompt,overwrite}
                        whether to overwrite the existing config. options are
                        "dryrun", "prompt", "overwrite". (default 'prompt')
```

## Validation
Validation is done in two parts. First, it checks the config file against the schema for basic things (e.g. "is this field the right data type?"). Then it checks more complex rules (e.g. "is at least one of {ipv4,ipv6} defined?"). If either step fails, it will print a descriptive error and exit, and no files will be created or modified.

## Modes of Operation
There are 3 modes of operation: `dryrun`, `prompt`, and `overwrite`. In each mode, the tool will validate the config file, generate the "output" config, and diff the existing on-disk config (if it exists) with the config it just generated. After that, the functionality diverges.
 
* `dryrun` prints the diff and exits
* `prompt` prints the diff and asks if you want to overwrite the generated configs (defaulting to no)
* `overwrite` overwrites the generated configs and exits

## Roadmap
The short-term goal is to support generating all config that I could reasonably need. This includes things like:
* more complete BGP support
* more complex routing policy capabilities
* support for OSPF
* support for BFD

In the medium-term, I also want to introduce some quality-of-life features:
* support for IRR-based filter generation
* support for pulling data from PeeringDB
* config backup/rollback
* update checking

In the long-term, I would like to make this tool into a module that I can call from other code. That would enable me to generate routing config dynamically (e.g. from a database), feed it to this tool, and then create files on disk.

## Contribution
Pull requests and issues with feature requests are welcome. I work on this project in my spare time, so it may take some time for me to review.