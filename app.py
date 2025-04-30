from flask import Flask, render_template, request, redirect, url_for
import json
import requests
from datetime import datetime, timedelta
import os
from numpy.random import randint
from math import degrees, pi, floor, log10

# Create the application.
app = Flask(__name__)

# Some global variables
OS_DOMAIN, OS_USER_ID, USER_NAME, HOST = None, None, None, None
ACCESS_TOKEN, REFRESH_TOKEN, EXPIRES_AT = None, None, None
DID, WID, EID, CONFIG, FUNCTION = None, None, None, None, None

# Get your API keys from a json file
with open('oauth_key.json') as f: 
    oauth_keys = json.load(f)
    OAUTH_CLIENT_ID = oauth_keys['OAUTH_CLIENT_ID']
    OAUTH_CLIENT_SECRET = oauth_keys['OAUTH_CLIENT_SECRET']

# This app handles various functions, depending on the 'function' query parameter in the app extension action URL
def handleReturn(FUNCTION):
    if FUNCTION == 'elements':
        return redirect(url_for('elements'))
    elif FUNCTION == 'colors':
        return redirect(url_for('colors'))
    elif FUNCTION == 'robot':
        return redirect(url_for('robot'))
    elif FUNCTION == 'ajax':
        return redirect(url_for('ajax'))
    else:    
        return redirect(url_for('index'))

# === The main page ===
@app.route('/')
def index():
    # Just to test the API, lets get all the parts in this element
    response = requests.get(
        os.path.join(
            OS_DOMAIN, 
            "api/parts/d/{}/w/{}/e/{}/".format(
                DID, WID, EID
            )
        ), 
        headers={
            "Content-Type": "application/json", 
            "Accept": "application/json;charset=UTF-8;qs=0.09", 
            "Authorization": "Bearer " + ACCESS_TOKEN
        }
    )
    
    PARTS = []
    if response.ok: 
        response = response.json() 
        for p in response:
            arr = [p["name"], p["partId"]]
            PARTS.append(arr)

    return render_template('index.html', parts=PARTS)

# === AJAX Testing ===
@app.route('/ajax')
def ajax():
    return render_template('ajax.html', DID=DID, EID=EID, WID=WID, ACCESS_TOKEN=ACCESS_TOKEN)

# === Move robot mates ===
@app.route('/robot')
def robot():
    # Get the current mate values
    response = requests.get(
        os.path.join(
            OS_DOMAIN,
            "api/assemblies/d/{}/w/{}/e/{}/matevalues".format(
            DID, WID, EID
            )
        ),
        headers={
            "Accept": "application/json;charset=UTF-8; qs=0.09",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + ACCESS_TOKEN
        }
    )

    MATES = []
    MATES_DEG = []

    response = response.json()
    # I'm interested in mates that start with "Arm"
    for mate in response["mateValues"]:
        if mate['mateName'].split('_')[0] == "Arm":
            MATES.append(mate)

    msg = ""
    # If we are getting here from the reset button, set all mate values to zero
    if request.args.get('reset'):
        msg = "Reset"
        for mate in MATES:
            mate['rotationZ'] = 0
            MATES_DEG.append((mate['mateName'],0))

    # If we are getting here from the add pi/8 button, add pi/8
    if request.args.get('mate_values'):
        msg = request.args.get('mate_values')
        for mate in MATES:
            mate['rotationZ'] = mate['rotationZ'] + pi/8
            MATES_DEG.append((mate['mateName'],round(degrees(mate['rotationZ'])),3))

    # Either way, update the mates
    if request.args.get('mate_values') or request.args.get('reset'):

        response = requests.post(
            os.path.join(
                OS_DOMAIN,
                "api/assemblies/d/{}/w/{}/e/{}/matevalues".format(
                DID, WID, EID
                )
            ),
            headers={
                "Accept": "application/json;charset=UTF-8; qs=0.09",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + ACCESS_TOKEN
            },
            json = {"mateValues":MATES}
        )
        response = response.json()        
    
    else:
        for mate in MATES:
            MATES_DEG.append((mate['mateName'],round(degrees(mate['rotationZ']),3)))

    return render_template('robot.html', mate_values = MATES_DEG, msg=msg)

# === List elements in the workspace ===
@app.route('/elements')
def elements():
    # Just to test the API, lets get all of the elements in the workspace
    response = requests.get(
        os.path.join(
            OS_DOMAIN,
            "api/documents/d/{}/w/{}/elements".format(
                DID, WID
            )
        ), 
        headers={
            "Content-Type": "application/json", 
            "Accept": "application/json;charset=UTF-8;qs=0.09", 
            "Authorization": "Bearer " + ACCESS_TOKEN
        }
    )
    
    ELEMENTS = []
    if response.ok: 
        response = response.json() 
        for e in response:
            arr = [e["name"], e["elementType"]]
            ELEMENTS.append(arr) 

    return render_template('elements.html', elements=ELEMENTS)

# === Part color shuffler ===
@app.route('/colors')
def colors():
    # Return a page that shows successful color shuffle
    global USER_NAME
    global PARTS
    if request.args.get('pid'):
        PID = request.args.get('pid')
        newColor = {'red': randint(255), 'green': randint(255), 'blue': randint(255)}
        # Get the current part properties
        response = requests.get(
            os.path.join(
                OS_DOMAIN, 
                "api/metadata/d/{}/w/{}/e/{}/p/{}".format(
                    DID, WID, EID, PID
                )
            ), 
            headers={
                "Content-Type": "application/json", 
                "Accept": "application/json;charset=UTF-8;qs=0.09", 
                "Authorization": "Bearer " + ACCESS_TOKEN
            }
        )
        # Get the part properties for one particular part, given PID
        partMetaData = response.json()
        partProperties = partMetaData['properties']

        # Replace the color property for that part
        for i in range(len(partProperties)):
            if partProperties[i]['name'] == 'Appearance':
                partProperties[i]['value']['color'] = newColor
            
        partMetaData['properties'] = partProperties
        payload = partMetaData

        # Post the new properties
        response = requests.post(
            os.path.join(
                OS_DOMAIN, 
                "api/metadata/d/{}/w/{}/e/{}/p/{}".format(
                    DID, WID, EID, PID
                )
            ), 
            headers={
                "Content-Type": "application/json", 
                "Accept": "application/json;charset=UTF-8;qs=0.09", 
                "Authorization": "Bearer " + ACCESS_TOKEN
            },
            json=payload
        ) 

        if response.ok:
            for p in PARTS:
                if p[1] == PID:
                    r = f'{newColor["red"]:x}'
                    g = f'{newColor["green"]:x}'
                    b = f'{newColor["blue"]:x}'
                    p[2] = r + g + b

    else: 
        # Get the current Onshape parts
        response = requests.get(
            os.path.join(
                OS_DOMAIN, 
                "api/parts/d/{}/w/{}/e/{}/".format(
                    DID, WID, EID
                )
            ), 
            headers={
                "Content-Type": "application/json", 
                "Accept": "application/json;charset=UTF-8;qs=0.09", 
                "Authorization": "Bearer " + ACCESS_TOKEN
            }
        )
        # Create array of parts [name, PID, hex RGB color]
        if response.ok: 
            response = response.json() 
            PARTS = []
            for i in range(len(response)):
                r = f'{response[i]["appearance"]["color"]["red"]:x}'
                g = f'{response[i]["appearance"]["color"]["green"]:x}'
                b = f'{response[i]["appearance"]["color"]["blue"]:x}'
                arr = [response[i]["name"], response[i]["partId"], r + g + b]
                PARTS.append(arr)
    return render_template(
            "colors.html", parts=PARTS
    )

# The right panel app goes to this URL:
# http://localhost:8000/login
# And it sends these query string parameters:
# did={$documentId}&wvm={$workspaceOrVersion}&wvmid={$workspaceOrVersionId}&eid={$elementId}&config={$configuration}&function=something

# === Oauth stuff.  This happens first ===
@app.route("/login/")
def login():
    print("Logging in") 
    # When the app extension is first opened, this app page is called. 
    # It collects user information and redirects the user to Onshape's OAuth authorization page. 
    global ACCESS_TOKEN, REFRESH_TOKEN, EXPIRES_AT
    global OS_DOMAIN, OS_USER_ID, DID, WID, EID, CONFIG, FUNCTION, HOST

    # set the domain, user ID, DID, WID, EID, CONFIG, FUNCTION for use later
    OS_DOMAIN = request.args.get('server')
    OS_USER_ID = request.args.get('userId')
    DID = request.args.get('did')
    WID = request.args.get('wvmid')
    EID = request.args.get('eid')
    FUNCTION = request.args.get('function')
    extension_config = request.args.get('config')
    if extension_config == '{$configuration}':
        CONFIG = "Element not configured"
    else:
        CONFIG = extension_config
    HOST = request.host.split(':')[1]
    print(HOST)
    # If we don't have an access token, go get one.
    if not ACCESS_TOKEN: 
        return redirect(
            "https://oauth.onshape.com/oauth/authorize?response_type=code&client_id={}".format(
                OAUTH_CLIENT_ID.replace("=", "%3D")
            )
        )
    # If our access token has expired, go get a new one.
    elif datetime.now() >= EXPIRES_AT - timedelta(minutes=20): 
        response = requests.post(
            "https://oauth.onshape.com/oauth/token?grant_type=refresh_token&refresh_token={}&client_id={}&client_secret={}".format(
                REFRESH_TOKEN.replace('=', '%3D'), 
                OAUTH_CLIENT_ID.replace('=', '%3D'), 
                OAUTH_CLIENT_SECRET.replace('=', '%3D')
            ), 
            headers={'Content-Type': "application/x-www-form-urlencoded"}
        )
        response = response.json() 
        print(response)
        ACCESS_TOKEN = response['access_token']
        REFRESH_TOKEN = response['refresh_token']
        EXPIRES_AT = datetime.now() + timedelta(seconds=response['expires_in'])

    return handleReturn(FUNCTION)

@app.route("/oauthRedirect/")
def authorize(): 
    print("authorizing")
    # When the user authorizes the OAuth integration, Onshape's OAuth 
    # authorization page will redirect the user to this page, as registered as the redirect URL.
 
    auth_code = request.args.get('code')
    if not auth_code: 
        return "<p>User authentication failed!</p><p>Error: " + str(request.args.get('error')) + "</p>"
    
    # Use authorization code to get tokens 
    response = requests.post(
        "https://oauth.onshape.com/oauth/token?grant_type=authorization_code&code={}&client_id={}&client_secret={}".format(
            auth_code.replace('=', '%3D'), 
            OAUTH_CLIENT_ID.replace('=', '%3D'), 
            OAUTH_CLIENT_SECRET.replace('=', '%3D')
        ), 
        headers={'Content-Type': "application/x-www-form-urlencoded"}
    )
    response = response.json() 
    
    global ACCESS_TOKEN, REFRESH_TOKEN, EXPIRES_AT
    ACCESS_TOKEN = response['access_token']
    REFRESH_TOKEN = response['refresh_token']
    EXPIRES_AT = datetime.now() + timedelta(seconds=response['expires_in'])
    
    return handleReturn(FUNCTION)

# ===== API CALLS =====
@app.route('/get-vars')
def getvars():
    response = requests.get(
        os.path.join(
            OS_DOMAIN,
            "api/variables/d/{}/w/{}/e/{}/variables?includeValuesAndReferencedVariables=true".format(
                DID, WID, EID
            )
        ), 
        headers={
            "Content-Type": "application/json", 
            "Accept": "application/json;charset=UTF-8;qs=0.09", 
            "Authorization": "Bearer " + ACCESS_TOKEN
        }
    )
    
    VARIABLES = []
    if response.ok: 
        response = response.json() 
        VARIABLES = response

    return VARIABLES

@app.route('/get_assem_mass_props')
def get_assem_mass_props():
    response = requests.get(
        os.path.join(
            OS_DOMAIN,
            "api/assemblies/d/{}/w/{}/e/{}/massproperties".format(
                DID, WID, EID
            )
        ), 
        headers={
            "Content-Type": "application/json", 
            "Accept": "application/json;charset=UTF-8;qs=0.09", 
            "Authorization": "Bearer " + ACCESS_TOKEN
        }
    )
    
    centroid_array = []
    if response.ok: 
        response = response.json() 
        centroid_array = [str(sig_figs(val, 3)) for val in response["centroid"][0:3]]

    return centroid_array

def sig_figs(x, precision):
    x = float(x)
    return round(x, -int(floor(log10(abs(x)))) + (precision - 1))