from jinja2 import Template
from jsonschema import validate
import argparse, ipaddress, json, os, re, sys

def main(config_file, template_file, schema_file, output_path):
    with open(template_file, 'r') as file:
        template_text = file.read()

    with open(config_file, 'r') as file:
        config_text = file.read()
    config = json.loads(config_text)

    with open(schema_file, 'r') as file:
        schema_text = file.read()
    schema = json.loads(schema_text)

    # validate config
    validate(instance=config, schema=schema)
    for session in config['bgp_sessions']:
        # need at least one ip protocol version defined
        if not "ipv4" in session and not "ipv6" in session:
            print("ERROR: session \"" + session['name'] + "\" must define at least one of ipv4,ipv6")
            sys.exit(1)
        
        # no spaces in session name
        if " " in session['name']:
            print("ERROR: session \"" + session['name'] + "\" name must not contain spaces")
            sys.exit(1)
        
        # filtering is set up right
        if session['type'] == "customer" or session['type'] == "peer":
            if session['filtering_method'] == "irr-as-set":
                if "as-set" in session:
                    #TODO: generate prefix list from IRR
                    print("filtering with IRR is not implemented yet, sorry")
                    sys.exit(1)
                else:
                    print("ERROR: session \"" + session['name'] + "\" filtering method set to \"irr-as-set\". \"as-set\" must be defined.")
                    sys.exit(1)
            elif session['filtering_method'] == "irr-autnum":
                if "as-set" in session:
                    #TODO: generate prefix list from IRR
                    print("filtering with IRR is not implemented yet, sorry")
                    sys.exit(1)
                else:
                    print("ERROR: session \"" + session['name'] + "\" filtering method set to \"irr-autnum\". \"autnum\" must be defined.")
                    sys.exit(1)
            elif session['filtering_method'] == "prefix-list":
                if "ipv4" in session:
                    # validate prefixes
                    if "prefixes" in session['ipv4']:
                        prefixes_with_more_specifics = []
                        for prefix in session['ipv4']['prefixes']:
                            try:
                                prefix_parsed = ipaddress.IPv4Network(prefix, strict=True)
                            except ValueError:
                                print("ERROR: session \"" + session['name'] + "\" ipv4 prefix \"" + prefix + "\" is not valid")
                                sys.exit(1)
                            if prefix_parsed.prefixlen < 24:
                                prefixes_with_more_specifics.append(str(prefix_parsed) + "{" + str(prefix_parsed.prefixlen) + ",24}")
                            else:
                                prefixes_with_more_specifics.append(str(prefix_parsed))
                        session['ipv4']['prefixes_str'] = ", ".join(prefixes_with_more_specifics)
                    else:
                        print("ERROR: session \"" + session['name'] + "\" filtering method set to \"prefix-list\". ipv4 section is defined and therefore must contain prefix list.")
                        sys.exit(1)
                if "ipv6" in session:
                    # validate prefixes
                    if "prefixes" in session['ipv6']:
                        prefixes_with_more_specifics = []
                        for prefix in session['ipv6']['prefixes']:
                            try:
                                prefix_parsed = ipaddress.IPv6Network(prefix, strict=True)
                            except ValueError:
                                print("ERROR: session \"" + session['name'] + "\" ipv6 prefix \"" + prefix + "\" is not valid")
                                sys.exit(1)
                            if prefix_parsed.prefixlen < 48:
                                prefixes_with_more_specifics.append(str(prefix_parsed) + "{" + str(prefix_parsed.prefixlen) + ",48}")
                            else:
                                prefixes_with_more_specifics.append(str(prefix_parsed))
                        session['ipv6']['prefixes_str'] = ", ".join(prefixes_with_more_specifics)
                    else:
                        print("ERROR: session \"" + session['name'] + "\" filtering method set to \"prefix-list\". ipv4 section is defined and therefore must contain prefix list.")
                        sys.exit(1)
            else:
                print("ERROR: session \"" + session['name'] + "\" filtering method set to unrecognised value. this should have been caught by json schema validation.")
                sys.exit(1)


    # render template
    t = Template(template_text)

    for session in config['bgp_sessions']:
        conf = t.render(session=session, trim_blocks=True, lstrip_blocks=True)
        conf = re.sub(r'\n\s*\n', '\n', conf)
        conf = re.sub(r'}\n', '}\n\n', conf)
        with open(os.path.join(output_path, "bgp_" + session['type'] + "_" + session['name'] + ".conf"), 'w') as writer:
            writer.write(conf)

if __name__ == "__main__":
    parser=argparse.ArgumentParser()

    parser.add_argument('--config', help='json file with information used to generate router config', type=str, required=True)
    parser.add_argument('--template', help='jinja2 template providing the config structure', type=str, required=True)
    parser.add_argument('--schema', help='json schema used to validate the config file', type=str, required=True)
    parser.add_argument('--outputFolder', help='folder where generated files go', type=str, required=True)

    args=parser.parse_args()

    main(args.config, args.template, args.schema, args.outputFolder)
