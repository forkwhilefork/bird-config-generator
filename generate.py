from jinja2 import Template
from jsonschema import validate
import argparse, ipaddress, json, os, re, sys

# What to indent with
INDENT_WITH = " " * 4 # 4 spaces
INDENT_PLUS = ["{"] # Characters that trigger indentation level+
INDENT_MINUS = ["}"] # Characters that trigger indentation level-

# thanks to FHR#6025 on BGPeople for this function
def bird_indent(conf):
    level = 0
    out = ""
    for line in conf.split('\n'):
        line = line.strip()

        # indent minus
        if sum(map(lambda x: x in line, INDENT_MINUS)) > 0:
            level -= 1
        
        out += f"{level * INDENT_WITH}{line}\n"
        
        # indent plus
        if sum(map(lambda x: x in line, INDENT_PLUS)) > 0:
            level += 1
   
    return(out)

def generate_config(config_file, template_file, schema_file):
    with open(template_file, 'r') as file:
        template_text = file.read()

    with open(config_file, 'r') as file:
        config_text = file.read()
    config = json.loads(config_text)

    with open(schema_file, 'r') as file:
        schema_text = file.read()
    schema = json.loads(schema_text)

    # validate config against schema
    validate(instance=config, schema=schema)

    # validate config against "business" logic
    for session in config['bgp_sessions']:
        # need at least one ip protocol version defined
        if not "ipv4" in session and not "ipv6" in session:
            print("ERROR: session \"" + session['name'] + "\" must define at least one of ipv4,ipv6")
            sys.exit(1)
        
        # no spaces in session name
        if " " in session['name']:
            print("ERROR: session \"" + session['name'] + "\" name must not contain spaces")
            sys.exit(1)
        # no dashes in session name
        if "-" in session['name']:
            print("ERROR: session \"" + session['name'] + "\" name must not contain \"-\"")
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
        
        # peer IPs should be valid
        if "ipv4" in session:
            try:
                ipaddress.IPv4Address(session['ipv4']['peer_ip'])
            except ValueError:
                print("ERROR: session \"" + session['name'] + "\" ipv4 peer IP \"" + session['ipv4']['peer_ip'] + "\" is not valid")
                sys.exit(1)
        if "ipv6" in session:
            try:
                ipaddress.IPv6Address(session['ipv6']['peer_ip'])
            except ValueError:
                print("ERROR: session \"" + session['name'] + "\" ipv6 peer IP \"" + session['ipv6']['peer_ip'] + "\" is not valid")
                sys.exit(1)
        
        # source IPs should be valid
        if "ipv4" in session and "source_ip" in session['ipv4']:
            try:
                ipaddress.IPv4Address(session['ipv4']['source_ip'])
            except ValueError:
                print("ERROR: session \"" + session['name'] + "\" ipv4 source IP \"" + session['ipv4']['source_ip'] + "\" is not valid")
                sys.exit(1)
        if "ipv6" in session and "source_ip" in session['ipv6']:
            try:
                ipaddress.IPv6Address(session['ipv6']['source_ip'])
            except ValueError:
                print("ERROR: session \"" + session['name'] + "\" ipv6 source IP \"" + session['ipv6']['source_ip'] + "\" is not valid")
                sys.exit(1)

        # ASN and local_pref are required if session type is not internal
        if session['type'] != "internal":
            if "asn" not in session:
                print("ERROR: session \"" + session['name'] + "\" is not type \"internal\" and therefore must have asn defined")
                sys.exit(1)
            if "local_pref" not in session:
                print("ERROR: session \"" + session['name'] + "\" is not type \"internal\" and therefore must have local_pref defined")
                sys.exit(1)

    for rpki in config['rpki_protocols']:
        # need at least one roa table version defined
        if not "roa4_table" in rpki and not "roa6_table" in rpki:
            print("ERROR: rpki protocol \"" + rpki['name'] + "\" must define at least one of roa4_table,roa6_table")
            sys.exit(1)
        
        # no spaces in protocol name
        if " " in rpki['name']:
            print("ERROR: rpki protocol \"" + rpki['name'] + "\" name must not contain spaces")
            sys.exit(1)
        # no dashes in protocol name
        if "-" in rpki['name']:
            print("ERROR: rpki protocol \"" + rpki['name'] + "\" name must not contain \"-\"")
            sys.exit(1)
        
        # ip should be valid
        try:
            ipaddress.IPv4Address(rpki['ip'])
        except ValueError:
            print("ERROR: rpki protocol \"" + rpki['name'] + "\" has invalid IP \"" + rpki['ip'] + "\"")
            sys.exit(1)

    for route in config['static_routes_v4']['routes']:
        # exactly one of {blackhole,next_hop} should be defined
        if (not "blackhole" in route and not "next_hop" in route) or ("blackhole" in route and "next_hop" in route):
            print("ERROR: static IPv4 route for \"" + route['destination'] + "\" must define exactly one of blackhole,next_hop")
            sys.exit(1)
        
        # destination and next_hop (if it exists) should be valid
        try:
            prefix_parsed = ipaddress.IPv4Network(route['destination'], strict=True)
        except ValueError:
            print("ERROR: static IPv4 route destination \"" + route['destination'] + "\" is not valid")
            sys.exit(1)

        # next_hop (if it exists) should be valid
        if "next_hop" in route:
            try:
                ipaddress.IPv4Address(route['next_hop'])
            except ValueError:
                print("ERROR: static IPv4 route \"" + route['destination'] + "\" has invalid next_hop \"" + route['next_hop'] + "\"")
                sys.exit(1)

    for route in config['static_routes_v6']['routes']:
        # exactly one of {blackhole,next_hop} should be defined
        if (not "blackhole" in route and not "next_hop" in route) or ("blackhole" in route and "next_hop" in route):
            print("ERROR: static IPv6 route for \"" + route['destination'] + "\" must define exactly one of blackhole,next_hop")
            sys.exit(1)
        
        # destination should be valid
        try:
            prefix_parsed = ipaddress.IPv6Network(route['destination'], strict=True)
        except ValueError:
            print("ERROR: static IPv6 route destination \"" + route['destination'] + "\" is not valid")
            sys.exit(1)

        # next_hop (if it exists) should be valid
        if "next_hop" in route:
            try:
                ipaddress.IPv6Address(route['next_hop'])
            except ValueError:
                print("ERROR: static IPv6 route \"" + route['destination'] + "\" has invalid next_hop \"" + route['next_hop'] + "\"")
                sys.exit(1)

    # render template
    t = Template(template_text)

    output = ""

    output = t.render(config=config, trim_blocks=True, lstrip_blocks=True)
    output = re.sub(r'\n\s*\n', '\n', output)
    output = re.sub(r'}\n', '}\n\n', output)
    output = bird_indent(output)
    
    return output

if __name__ == "__main__":
    parser=argparse.ArgumentParser()

    parser.add_argument('--config', help='json file with information used to generate router config', type=str, required=True, default='config.json')
    parser.add_argument('--template', help='jinja2 template providing the config structure', type=str, required=True, default='template.jinja2')
    parser.add_argument('--schema', help='json schema used to validate the config file', type=str, required=True, default='schema.json')
    parser.add_argument('--outputPath', help='path of generated file', type=str, required=True, default='.')
    parser.add_argument('--dryRun', help='check config validity but do not generate any files', type=bool, default=False)

    args=parser.parse_args()

    output = generate_config(args.config, args.template, args.schema)
    if not args.dryRun:
        with open(args.outputPath, 'w') as writer:
            writer.write(output)
