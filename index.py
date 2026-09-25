from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from google_play_scraper import app as gp_app

REGION_GROUPS = {
    "IND": "IND",
    "BR,US,NA,SAC": "AMERICA",
    "BD,PK,SG,ID,ME,VN,TH,TW,EU,RU": "OTHERS",
}


def _style(key: str) -> str:
    return "".join(c.upper() if i % 2 else c.lower() for i, c in enumerate(key))


def _get_latest_version(package_name="com.dts.freefireth", lang="fr", country="fr"):
    try:
        return gp_app(package_name, lang=lang, country=country)["version"]
    except Exception as e:
        raise Exception(f"Play Store se version nahi mila: {e}")


def _fetch_api_data(version, region="ME"):
    url = "https://version.ggwhitehawk.com/live/ver.php"
    params = {
        "version": version,
        "lang": "en",
        "device": "android",
        "channel": "android",
        "appsttore": "googleplay",
        "region": region,
        "whitelist_version": "1.3.0",
        "whitelist_sp_version": "1.0.0",
        "device_name": "google G011A",
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def _build_client_url(server_url, region):
    r = region.upper()
    if r == "IND":
        return "client.ind.freefiremobile.com"
    if r in {"BR", "US", "NA", "SAC"}:
        return "client.us.freefiremobile.com"
    if "loginbp." in server_url:
        return server_url.replace("loginbp.", "clientbp.")
    return server_url


def _format_url(domain):
    if not domain.startswith("http"):
        domain = "https://" + domain
    if not domain.endswith("/"):
        domain += "/"
    return domain


def get_freefire_info(region="US", package_name="com.dts.freefireth", lang="fr", country="fr"):
    v = _get_latest_version(package_name, lang, country)
    d = _fetch_api_data(v)
    return {
        _style("play_ver"): d["remote_version"],
        _style("ob_ver"): d["latest_release_version"],
        _style("login_url"): d["server_url"],
        _style("client_url"): _build_client_url(d["server_url"], region),
    }


def get_categories():
    base = get_freefire_info("US")
    sv = base[_style("login_url")]
    rv = base[_style("ob_ver")]
    cv = base[_style("play_ver")]

    def client_domain(group):
        if group == "IND":
            return "client.ind.freefiremobile.com"
        if group == "AMERICA":
            return "client.us.freefiremobile.com"
        if "loginbp." in sv:
            return sv.replace("loginbp.", "clientbp.").replace("https://", "").rstrip("/")
        return sv.replace("https://", "").rstrip("/")

    return {
        region_ids: {
            _style("client_url"): _format_url(client_domain(group)),
            _style("login_url"): sv,
            _style("ob_ver"): rv,
            _style("play_ver"): cv,
        }
        for region_ids, group in REGION_GROUPS.items()
    }


app = FastAPI(title="Free Fire Info API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    try:
        return get_categories()
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/info")
def info(region: str = Query("US")):
    try:
        return get_freefire_info(region)
    except Exception as e:
        raise HTTPException(500, str(e))
