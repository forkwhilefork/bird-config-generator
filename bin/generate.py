from jinja2 import Template
import jsonschema
import argparse, difflib, ipaddress, json, os, re, sys, wasabi

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

# thanks to StackOverflow user fmark (https://stackoverflow.com/a/3041990) for this function
def query_yes_no(question, default="no"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")

# this function is borrowed (with some small modifications) from the difflib package
def colored_unified_diff(a, b, fromfile='', tofile='', fromfiledate='',
                tofiledate='', n=3, lineterm='\n'):
    difflib._check_types(a, b, fromfile, tofile, fromfiledate, tofiledate, lineterm)
    started = False
    for group in difflib.SequenceMatcher(None,a,b).get_grouped_opcodes(n):
        if not started:
            started = True
            fromdate = '\t{}'.format(fromfiledate) if fromfiledate else ''
            todate = '\t{}'.format(tofiledate) if tofiledate else ''
            yield wasabi.color('--- {}{}{}'.format(fromfile, fromdate, lineterm), fg=15)
            yield wasabi.color('+++ {}{}{}'.format(tofile, todate, lineterm), fg=15)

        first, last = group[0], group[-1]
        file1_range = difflib._format_range_unified(first[1], last[2])
        file2_range = difflib._format_range_unified(first[3], last[4])
        yield wasabi.color('@@ -{} +{} @@{}'.format(file1_range, file2_range, lineterm), fg="cyan")

        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                for line in a[i1:i2]:
                    yield ' ' + line
            elif tag == 'delete':
                for line in a[i1:i2]:
                    yield wasabi.color('-' + line, fg="red")
            elif tag == 'insert':
                for line in b[j1:j2]:
                    yield wasabi.color('+' + line, fg="green")
            elif tag == 'replace':
                # ideally we do something intelligent here to highlight changed words
                for line in a[i1:i2]:
                    yield wasabi.color('-' + line, fg="red")
                for line in b[j1:j2]:
                    yield wasabi.color('+' + line, fg="green")

def get_json_from_file(filename):
    with open(filename, 'r') as file:
        text = file.read()
    return json.loads(text)

def get_text_from_file(filename):
    with open(filename, 'r') as file:
        return file.read()

def generate_protocol_config(config, template_text):
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
            if not "filtering_method" in session:
                print("\"filtering_method\" must be set for session of type " + session['type'])
                sys.exit(1)
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

        # ASN is required if session type is not internal
        if session['type'] != "internal":
            if "asn" not in session:
                print("ERROR: session \"" + session['name'] + "\" is type \"" + session['type'] + "\" and therefore must have asn defined")
                sys.exit(1)

        # local_pref is required if session type is not internal or collector
        if session['type'] != "internal" and session['type'] != "collector":
            if "local_pref" not in session:
                print("ERROR: session \"" + session['name'] + "\" is type \"" + session['type'] + "\" and therefore must have local_pref defined")
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

    for route in config['static_routes_v4']:
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

    for route in config['static_routes_v6']:
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

def generate_constants_config(config, template_text):
    # Since ASNs are 4 bytes, and python integers are 4 bytes,
    # we don't have to check that the ASN is in the allowed range.
    # Note: we're not checking for bogon ASNs here. A user may want to
    # operate with a private ASN or something.

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

    parser.add_argument('--config', help='json file with information used to generate router config (default \'config.json\')', type=str, required=True, default='config.json')
    parser.add_argument('--outputPath', help='path of generated file (default \'.\')', type=str, required=True, default='.')
    parser.add_argument('--mode', help='whether to overwrite the existing config. options are "dryrun", "prompt", "overwrite".  (default \'prompt\')', type=str, default='prompt', choices=['dryrun', 'prompt', 'overwrite'])

    args=parser.parse_args()

    # get absolute path of this tool
    base_folder_path = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

    # get config object
    config = get_json_from_file(args.config)

    # get schema object
    schema = get_json_from_file(os.path.join(base_folder_path, "schema.json"))

    try:
        # validate config against schema
        jsonschema.validate(instance=config, schema=schema)
    except json.decoder.JSONDecodeError:
        print("invalid JSON")
        sys.exit(1)
    except jsonschema.exceptions.ValidationError as e:
        print("ERROR: JSON does not validate against schema")
        print(e.message)
        print("On instance " + jsonschema._utils.format_as_index(e.relative_path))
        print(e.instance)
        sys.exit(1)
    
    
    protocols_template = get_text_from_file(os.path.join(os.path.join(base_folder_path, "templates"), "protocols.jinja2"))
    constants_template = get_text_from_file(os.path.join(os.path.join(base_folder_path, "templates"), "constants.jinja2"))

    protocols_output = generate_protocol_config(config, protocols_template)
    constants_output = generate_constants_config(config, constants_template)

    files_to_compare = [
        (os.path.join(args.outputPath, "protocols.conf"), protocols_output),
        (os.path.join(args.outputPath, "user_constants.conf"), constants_output)
        ]
    files_with_changes = []

    for path, generated in files_to_compare:
        # read existing config
        existing_config = ''
        file_exists = True
        try:
            with open(path, 'r') as file:
                existing_config = file.read()
        except FileNotFoundError:
            file_exists = False
        else:
            # collect changes into a list so we can count them easily
            lines = list(colored_unified_diff(existing_config.split("\n"), generated.split("\n"), fromfile="a/"+path, tofile="b/"+path, lineterm=""))

            # if there are no changes, tell the user and exit
            if len(lines) == 0:
                print(wasabi.color("** " + path + " has no changes", fg=11))
                continue
            else:
                files_with_changes.append(path)
            
            # compare with output
            for line in lines:
                print(line)
            
            # add a newline for readability
            print()
        
        # if the file isn't there, tell the user
        if not file_exists:
            files_with_changes.append(path)
            print(wasabi.color("** " + path + " will be a new file", fg=11))
        

    if args.mode == 'dryrun':
        # just exit
        print(wasabi.color("** mode is dryrun; exiting without writing files", fg=11))
        sys.exit(0)

    write = False
    if args.mode == 'prompt' and len(files_with_changes)>0:
        # prompt for confirmation
        if query_yes_no(wasabi.color("** proceed with changes?", fg=11)):
            write = True

    # if we decided above to write the files, or if we are in overwrite mode, then write the files
    if write or args.mode == 'overwrite':
        for path, generated in files_to_compare:
            # only write a file if it has changed
            if path in files_with_changes:
                with open(path, 'w') as writer:
                    writer.write(generated)
                print(wasabi.color("** wrote file " + path, fg=11))
