# La signature de l'app pour TestFlight, par l'API App Store Connect, avec la seule clé d'API (action iPad) :
# l'identifiant de l'app, un certificat Apple Distribution pour la clé privée de l'action (cle.pem), un profil
# App Store. Écrit cert.cer, profil.mobileprovision et signature.env (TEAM, PROFIL).
# Rien que la bibliothèque standard et openssl : la signature du jeton (ES256) passe par openssl.
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.appstoreconnect.apple.com/v1"
KID, ISS, BUNDLE = os.environ["ASC_KEY_ID"], os.environ["ASC_ISSUER_ID"], os.environ["BUNDLE"]


def openssl(*args, data=None):
    return subprocess.run(["openssl", *args], input=data, capture_output=True, check=True).stdout


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def jeton():
    """Le jeton de l'API : ES256, signé par la clé d'API (asc.p8)."""
    now = int(time.time())
    msg = b64(json.dumps({"alg": "ES256", "kid": KID, "typ": "JWT"}).encode()) + b"." + \
        b64(json.dumps({"iss": ISS, "iat": now, "exp": now + 1100, "aud": "appstoreconnect-v1"}).encode())
    der = openssl("dgst", "-sha256", "-sign", "asc.p8", data=msg)
    # openssl rend une SEQUENCE DER de deux INTEGER (r, s) ; le jeton veut r || s, 32 octets chacun
    rs, p = [], 2
    for _ in range(2):
        n = der[p + 1]
        rs.append(int.from_bytes(der[p + 2:p + 2 + n], "big"))
        p += 2 + n
    return (msg + b"." + b64(rs[0].to_bytes(32, "big") + rs[1].to_bytes(32, "big"))).decode()


TOKEN = jeton()


def api(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r) if r.status != 204 else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        try:
            detail = "; ".join(x.get("detail", x.get("title", "")) for x in json.loads(detail)["errors"])
        except (ValueError, KeyError, TypeError):
            pass
        sys.exit(f"{method} {path.split('?')[0]} : {e.code} {detail}")


def modulus(pem_or_der, *kind):
    return openssl(*kind, "-noout", "-modulus", data=pem_or_der).strip()


# l'identifiant de l'app (créé s'il manque)
bundle = next((b for b in api("GET", f"/bundleIds?filter[identifier]={BUNDLE}&limit=200")["data"]
               if b["attributes"]["identifier"] == BUNDLE), None)
if not bundle:
    bundle = api("POST", "/bundleIds", {"data": {"type": "bundleIds", "attributes": {
        "identifier": BUNDLE, "name": "FM-1", "platform": "IOS"}}})["data"]

# le certificat de la clé de l'action, s'il est encore valable plus d'une semaine ; sinon un nouveau
cle = open("cle.pem", "rb").read()
mien = modulus(cle, "rsa")
limite = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() + 7 * 86400))
cert = next((c for c in api("GET", "/certificates?filter[certificateType]=DISTRIBUTION&limit=200")["data"]
             if c["attributes"]["expirationDate"][:19] > limite
             and modulus(base64.b64decode(c["attributes"]["certificateContent"]), "x509", "-inform", "der") == mien), None)
if not cert:
    csr = openssl("req", "-new", "-key", "cle.pem", "-subj", "/CN=FM-1 TestFlight").decode()
    cert = api("POST", "/certificates", {"data": {"type": "certificates", "attributes": {
        "certificateType": "DISTRIBUTION", "csrContent": csr}}})["data"]
open("cert.cer", "wb").write(base64.b64decode(cert["attributes"]["certificateContent"]))

# le profil App Store de ce certificat ; un profil de ce nom qui n'est plus valable est remplacé
nom = "FM-1 TestFlight " + cert["id"]
profils = [p for p in api("GET", f"/profiles?filter[name]={urllib.parse.quote(nom)}&limit=200")["data"] if p["attributes"]["name"] == nom]
profil = next((p for p in profils if p["attributes"]["profileState"] == "ACTIVE"), None)
if not profil:
    for p in profils:
        api("DELETE", "/profiles/" + p["id"])
    profil = api("POST", "/profiles", {"data": {"type": "profiles", "attributes": {"name": nom, "profileType": "IOS_APP_STORE"},
                                                "relationships": {"bundleId": {"data": {"type": "bundleIds", "id": bundle["id"]}},
                                                                  "certificates": {"data": [{"type": "certificates", "id": cert["id"]}]}}}})["data"]
open("profil.mobileprovision", "wb").write(base64.b64decode(profil["attributes"]["profileContent"]))

# l'équipe, d'après le certificat (OU du sujet)
sujet = openssl("x509", "-inform", "der", "-noout", "-subject", "-nameopt", "multiline", data=open("cert.cer", "rb").read()).decode()
team = next(l.split("=", 1)[1].strip() for l in sujet.splitlines() if l.strip().startswith("organizationalUnitName"))
with open("signature.env", "w") as env:
    env.write(f"TEAM={team}\nPROFIL={profil['attributes']['uuid']}\n")
print(f"certificat {cert['id']} (jusqu'au {cert['attributes']['expirationDate'][:10]}), profil {profil['attributes']['uuid']}, équipe {team}")
