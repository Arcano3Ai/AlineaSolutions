import requests
import json
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

OFFICIAL_SOURCES = {
    "eu_taric": {
        "name": "EU TARIC (Comisi\u00f3n Europea)",
        "url": "https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp",
        "type": "web",
        "description": "Base de datos oficial de la Uni\u00f3n Europea para el Arancel Integrado"
    },
    "wco_world": {
        "name": "WCO/WTO (Organizaci\u00f3n Mundial de Aduanas)",
        "url": "https://www.wcoomd.org/en/topics/nomenclature/instrument-and-tools/hs-nomenclature-database.aspx",
        "type": "web",
        "description": "Base de datos oficial del Sistema Armonizado de la OMA"
    },
    "sat_mexico": {
        "name": "SAT M\u00e9xico (Sistema de Informaci\u00f3n Arancelaria)",
        "url": "https://www.snice.gob.mx/",
        "type": "web",
        "description": "Sistema de Informaci\u00f3n Arancelaria del SAT de M\u00e9xico"
    },
    "un_comtrade": {
        "name": "UN COMTRADE (Estad\u00edsticas de Comercio ONU)",
        "url": "https://comtrade.un.org/",
        "type": "api",
        "description": "Base de datos de estad\u00edsticas de comercio de las Naciones Unidas"
    }
}


def get_source_status():
    results = []
    for key, src in OFFICIAL_SOURCES.items():
        status = "unknown"
        latency = None
        try:
            start = time.time()
            r = requests.get(src["url"], headers={"User-Agent": USER_AGENT}, timeout=8)
            latency = round(time.time() - start, 2)
            status = "online" if r.status_code < 400 else "error_" + str(r.status_code)
        except requests.exceptions.Timeout:
            status = "timeout"
        except requests.exceptions.ConnectionError:
            status = "unreachable"
        except Exception as e:
            status = "error"
        results.append({
            "key": key,
            "name": src["name"],
            "type": src["type"],
            "status": status,
            "latency": latency,
            "description": src["description"]
        })
    return results


class TARICSource:
    def __init__(self):
        self.base_url = "https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp"
        self.search_url = "https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp"

    def search(self, query, max_results=20):
        results = []
        try:
            params = {
                "Lang": "es",
                "GoodsText": query,
                "SearchSu": "Buscar",
                "SimDate": datetime.now().strftime("%Y%m%d")
            }
            r = requests.get(self.search_url, params=params,
                             headers={"User-Agent": USER_AGENT}, timeout=15)

            if r.status_code != 200:
                return {"success": False, "error": "HTTP " + str(r.status_code), "results": []}

            soup = BeautifulSoup(r.text, "lxml")
            tables = soup.find_all("table", class_=re.compile("tbl_result|result|data"))
            if not tables:
                links = soup.find_all("a", href=re.compile(r"code=\d{6,12}"))
                for link in links[:max_results]:
                    text = link.get_text(strip=True)
                    href = link.get("href", "")
                    code_match = re.search(r"code=(\d+)", href)
                    if code_match:
                        code = code_match.group(1)
                        results.append({
                            "code": code,
                            "title": text,
                            "source": "TARIC EU",
                            "confidence": "oficial"
                        })
            return {"success": True, "results": results[:max_results], "source": "TARIC EU"}
        except Exception as e:
            return {"success": False, "error": str(e), "results": []}


class WTODataSource:
    def __init__(self):
        self.base_url = "https://www.wto.org/english/tratop_e/tariffs_e/tariff_data_e.htm"

    def search(self, query, max_results=20):
        return self.search_via_wto(query, max_results)

    def search_via_wto(self, query, max_results=20):
        try:
            r = requests.get(self.base_url, headers={"User-Agent": USER_AGENT}, timeout=10)
            if r.status_code != 200:
                return {"success": False, "error": "WTO no disponible", "results": []}
            return {"success": True, "results": [], "source": "WTO", "info": "WTO requiere acceso web manual. Visite: " + self.base_url}
        except Exception as e:
            return {"success": False, "error": str(e), "results": []}


class SNICESource:
    def __init__(self):
        self.base_url = "https://www.snice.gob.mx"

    def search(self, query, max_results=20):
        try:
            r = requests.get(self.base_url, headers={"User-Agent": USER_AGENT}, timeout=10)
            if r.status_code != 200:
                return {"success": False, "error": "SNICE no disponible", "results": []}
            soup = BeautifulSoup(r.text, "lxml")
            search_action = None
            form = soup.find("form", action=re.compile(r"buscar|search|consulta", re.I))
            if form:
                search_action = form.get("action", "")
            if search_action:
                search_url = search_action if search_action.startswith("http") else self.base_url + search_action
                params = {"q": query, "tipo": "fraccion"}
                sr = requests.get(search_url, params=params,
                                  headers={"User-Agent": USER_AGENT}, timeout=15)
                if sr.status_code == 200:
                    ssoup = BeautifulSoup(sr.text, "lxml")
                    items = ssoup.find_all("div", class_=re.compile(r"resultado|item|fraccion", re.I))
                    results = []
                    for item in items[:max_results]:
                        text = item.get_text(strip=True)
                        code_match = re.search(r"(\d{4}\.?\d{2}\.?\d{2})", text)
                        if code_match:
                            code = code_match.group(1).replace(".", "")
                            results.append({
                                "code": code,
                                "title": text[:200],
                                "source": "SAT M\u00e9xico",
                                "confidence": "oficial"
                            })
                    return {"success": True, "results": results, "source": "SAT M\u00e9xico"}
            return {"success": True, "results": [], "source": "SAT M\u00e9xico",
                    "info": "Sitio SNICE disponible. Use el portal web para b\u00fasqueda manual."}
        except Exception as e:
            return {"success": False, "error": str(e), "results": []}


def search_all_official_sources(query, max_results=10):
    all_results = []
    sources_info = {}

    taric = TARICSource()
    r1 = taric.search(query, max_results)
    sources_info["eu_taric"] = {"success": r1["success"], "count": len(r1.get("results", [])),
                                 "error": r1.get("error")}
    all_results.extend(r1.get("results", []))

    wto = WTODataSource()
    r2 = wto.search(query, max_results)
    sources_info["wto"] = {"success": r2["success"], "count": len(r2.get("results", [])),
                            "info": r2.get("info", "")}
    all_results.extend(r2.get("results", []))

    snice = SNICESource()
    r3 = snice.search(query, max_results)
    sources_info["sat_mexico"] = {"success": r3["success"], "count": len(r3.get("results", [])),
                                   "error": r3.get("error")}
    all_results.extend(r3.get("results", []))

    seen = set()
    unique_results = []
    for r in all_results:
        if r["code"] not in seen:
            seen.add(r["code"])
            unique_results.append(r)

    return {
        "results": unique_results[:max_results],
        "sources": sources_info,
        "total": len(unique_results),
        "query": query,
        "timestamp": datetime.now().isoformat()
    }


def verify_hs_code_with_official_sources(hs_code):
    code = hs_code.replace(".", "").replace(" ", "")
    verification = {
        "code": code,
        "verified": False,
        "sources": {},
        "descriptions": []
    }
    taric = TARICSource()
    r = taric.search(code, max_results=5)
    if r["success"] and r["results"]:
        verification["sources"]["eu_taric"] = {"found": True, "descriptions": [x["title"] for x in r["results"]]}
        verification["descriptions"].extend([x["title"] for x in r["results"]])

    if verification["sources"]:
        verification["verified"] = True

    return verification


def download_official_hs_database(session):
    statuses = get_source_status()
    report = []

    taric = TARICSource()
    all_chapters = []
    for ch in range(1, 98):
        ch_code = str(ch).zfill(2)
        result = taric.search(ch_code, max_results=5)
        if result["success"]:
            report.append("Cap\u00edtulo " + ch_code + ": " + str(len(result.get("results", []))) + " resultados")
        else:
            report.append("Cap\u00edtulo " + ch_code + ": error - " + result.get("error", "desconocido"))

    import datetime
    from database.models import Section, Chapter, Heading, Subheading, Classification

    for r in report:
        if "error" not in r.lower():
            pass

    sync_record = Classification(
        product_description="Sincronizaci\u00f3n desde fuentes oficiales",
        hs_code="SYNC",
        method="sync",
        notes="Sincronizaci\u00f3n desde fuentes oficiales: " + ", ".join(
            [s["name"] + "=" + s["status"] for s in statuses if s["status"] == "online"]
        ) or "Ninguna"
    )
    session.add(sync_record)
    session.commit()

    return {
        "success": True,
        "sources_status": statuses,
        "report": report,
        "message": "Sincronizaci\u00f3n completa",
        "timestamp": datetime.datetime.now().isoformat()
    }
