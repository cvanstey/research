import os
import re
import hashlib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State
import wbgapi as wb
import pycountry
from functools import lru_cache

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "data",
    "undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx")

if not os.path.exists(FILE_PATH):
    FILE_PATH = r"C:\Users\crook\PROJECTS\PythonProject_OCR\scans\undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx"

BASE_YEARS    = ["1990", "1995", "2000", "2005", "2010", "2015", "2020", "2024"]
SUFFIX_TO_SEX = {"": "_total", ".1": "_male", ".2": "_female"}

ID_COLS = [
    "region_development_group_country_or_area_of_destination",
    "region_development_group_country_or_area_of_origin",
    "location_code_of_destination",
    "location_code_of_origin",
    "coverage",
    "data_type",
]

EXCLUDE_KEYWORDS = [
    "World", "Region", "developed", "developing", "income", "Others",
    "UN ", "Europe", "Oceania", "Caribbean", "Channel",
    "Central America", "South America",
    "Sub-Saharan", "Northern Africa", "Eastern Africa", "ASIA", "AFRICA",
    "Western Africa", "Central Africa", "Southern Africa",
    "Northern America", "Latin America", "Australia/New Zealand",
    "Land-Locked", "LLDC", "Least Developed",
]

PALETTE = [
    "#0072B2", "#E69F00", "#009E73", "#CC79A7",
    "#D55E00", "#56B4E9", "#F0E442", "#000000",
]

COUNTRY_NAME_MAP = {
    "United States of America":                              "United States",
    "United Kingdom of Great Britain and Northern Ireland":  "United Kingdom",
    "Iran (Islamic Republic of)":                            "Iran",
    "Republic of Korea":                                     "South Korea",
    "Democratic People's Republic of Korea":                 "North Korea",
    "Dem. People's Republic of Korea":                       "North Korea",
    "Viet Nam":                                              "Vietnam",
    "Syrian Arab Republic":                                  "Syria",
    "Russian Federation":                                    "Russia",
    "Bolivia (Plurinational State of)":                      "Bolivia",
    "Brunei Darussalam":                                     "Brunei",
    "Congo":                                                 "Congo",
    "Congo, Democratic Republic of the":                     "DR Congo",
    "Democratic Republic of the Congo":                      "DR Congo",
    "Bahamas":                                               "Bahamas",
    "Gambia":                                                "Gambia",
    "Egypt":                                                 "Egypt",
    "Kyrgyzstan":                                            "Kyrgyzstan",
    "Lao People's Democratic Republic":                      "Laos",
    "Slovakia":                                              "Slovakia",
    "Yemen":                                                 "Yemen",
    "Côte d'Ivoire":                                         "Ivory Coast",
    "Cote d'Ivoire":                                         "Ivory Coast",
    "Czechia":                                               "Czech Republic",
    "China, Hong Kong SAR":                                  "Hong Kong",
    "China, Macao SAR":                                      "Macao",
    "China, Taiwan Province of China":                       "Taiwan",
    "Eswatini":                                              "Swaziland",
    "Cabo Verde":                                            "Cape Verde",
    "Timor-Leste":                                           "East Timor",
    "Türkiye":                                               "Turkey",
    "State of Palestine":                                    "Palestine",
    "Micronesia (Federated States of)":                      "Micronesia",
    "Venezuela (Bolivarian Republic of)":                    "Venezuela",
    "Tanzania, United Republic of":                          "Tanzania",
    "Republic of Moldova":                                   "Moldova",
}

UN_TO_WB = {
    "United States of America":                              "United States",
    "United Kingdom of Great Britain and Northern Ireland":  "United Kingdom",
    "Russian Federation":                                    "Russia",
    "Syrian Arab Republic":                                  "Syria",
    "Tanzania, United Republic of":                         "Tanzania",
    "Venezuela (Bolivarian Republic of)":                    "Venezuela",
    "Republic of Moldova":                                   "Moldova",
    "Türkiye":                                               "Turkey",
    "Bolivia (Plurinational State of)":                      "Bolivia",
    "Bahamas":                                               "Bahamas, The",
    "China, Hong Kong SAR":                                  "Hong Kong SAR, China",
    "China, Macao SAR":                                      "Macao SAR, China",
    "Congo":                                                 "Congo, Rep.",
    "Congo, Democratic Republic of the":                     "Congo, Dem. Rep.",
    "Democratic Republic of the Congo":                      "Congo, Dem. Rep.",
    "Egypt":                                                 "Egypt, Arab Rep.",
    "Gambia":                                                "Gambia, The",
    "Iran (Islamic Republic of)":                            "Iran, Islamic Rep.",
    "Republic of Korea":                                     "Korea, Rep.",
    "Democratic People's Republic of Korea":                 "Korea, Dem. People's Rep.",
    "Dem. People's Republic of Korea":                       "Korea, Dem. People's Rep.",
    "Kyrgyzstan":                                            "Kyrgyz Republic",
    "Lao People's Democratic Republic":                      "Lao PDR",
    "Slovakia":                                              "Slovak Republic",
    "Viet Nam":                                              "Vietnam",
    "Yemen":                                                 "Yemen, Rep.",
    "China, Taiwan Province of China":                       "Taiwan, China",
    "Côte d'Ivoire":                                         "Cote d'Ivoire",
    "Curaçao":                                               "Curacao",
    "Falkland Islands (Malvinas)":                           "Falkland Islands",
    "Anguilla":                                              "Anguilla",
    "Bonaire, Sint Eustatius and Saba":                      "Bonaire, Sint Eustatius and Saba",
    "Cook Islands":                                          "Cook Islands",
    "State of Palestine":                                    "West Bank and Gaza",
    "Somalia":                                               "Somalia, Fed. Rep.",
    "United Republic of Tanzania":                           "Tanzania",
    "Puerto Rico":                                           "Puerto Rico",
}

PLOTLY_NAME_MAP = {
    "United States of America":                             "United States",
    "United Kingdom of Great Britain and Northern Ireland": "United Kingdom",
    "Russian Federation":                                   "Russia",
    "Iran (Islamic Republic of)":                           "Iran",
    "Syrian Arab Republic":                                 "Syria",
    "Viet Nam":                                             "Vietnam",
    "Republic of Korea":                                    "South Korea",
    "Democratic People's Republic of Korea":                "North Korea",
    "Dem. People's Republic of Korea":                      "North Korea",
    "Bolivia (Plurinational State of)":                     "Bolivia",
    "Venezuela (Bolivarian Republic of)":                   "Venezuela",
    "Tanzania, United Republic of":                         "Tanzania",
    "Congo, Democratic Republic of the":                    "Democratic Republic of the Congo",
    "Democratic Republic of the Congo":                     "Democratic Republic of the Congo",
    "Lao People's Democratic Republic":                     "Laos",
    "Republic of Moldova":                                  "Moldova",
    "Türkiye":                                              "Turkey",
}

MANUAL_ISO3 = {
    "Anguilla":                         "AIA",
    "Bonaire, Sint Eustatius and Saba": "BES",
    "Cook Islands":                     "COK",
    "Falkland Islands (Malvinas)":      "FLK",
    "French Guiana":                    "GUF",
    "Guadeloupe":                       "GLP",
    "Martinique":                       "MTQ",
    "Mayotte":                          "MYT",
    "Puerto Rico":                      "PRI",
    "Niue":                             "NIU",
    "Tokelau":                          "TKL",
    "Montserrat":                       "MSR",
    "Saint Pierre and Miquelon":        "SPM",
    "Gibraltar":                        "GIB",
    "Isle of Man":                      "IMN",
    "Bermuda":                          "BMU",
    "Tuvalu":                           "TUV",
    "American Samoa":                   "ASM",
    "Cayman Islands":                   "CYM",
    "Marshall Islands":                 "MHL",
    "San Marino":                       "SMR",
    "Andorra":                          "AND",
    "Liechtenstein":                    "LIE",
    "United Kingdom":                   "GBR",
    "Central African Republic":         "CAF",
    "South Africa":                     "ZAF",
    "China, Hong Kong SAR":             "HKG",
    "China, Macao SAR":                 "MAC",
    "China, Taiwan Province of China":  "TWN",
    "Holy See":                         "VAT",
    "Saint Helena":                     "SHN",
    "State of Palestine":               "PSE",
    "United States Virgin Islands":     "VIR",
    "Wallis and Futuna Islands":        "WLF",
    "Russia":                           "RUS",
    "South Korea":                      "KOR",
    "North Korea":                      "PRK",
    "Vietnam":                          "VNM",
    "Iran":                             "IRN",
    "Syria":                            "SYR",
    "Bolivia":                          "BOL",
    "Venezuela":                        "VEN",
    "Tanzania":                         "TZA",
    "Moldova":                          "MDA",
    "Turkey":                           "TUR",
    "Laos":                             "LAO",
    "DR Congo":                         "COD",
    "United States":                    "USA",
    "Côte d'Ivoire":                    "CIV",
    "Ivory Coast":                      "CIV",
    "Congo":                            "COG",
    "Democratic Republic of the Congo": "COD",
    "United Republic of Tanzania":      "TZA",
    "Eswatini":                         "SWZ",
    "Cabo Verde":                       "CPV",
    "São Tomé and Príncipe":            "STP",
    "Réunion":                          "REU",
    "Western Sahara":                   "ESH",
    "Eritrea":                          "ERI",
    "Somalia":                          "SOM",
    "Libya":                            "LBY",
    "Egypt":                            "EGY",
    "Sudan":                            "SDN",
    "South Sudan":                      "SSD",
    "Gambia":                           "GMB",
}

dest_col   = "region_development_group_country_or_area_of_destination"
origin_col = "region_development_group_country_or_area_of_origin"

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_col(name):
    return (
        str(name).replace("\n", " ").replace("\xa0", " ")
        .strip().lower().replace(" ", "_").replace(",", "")
    )

def rename_year_cols(columns):
    pat = re.compile(r"^(1990|1995|2000|2005|2010|2015|2020|2024)(\.\d)?$")
    out = []
    for c in columns:
        m = pat.match(str(c))
        if m:
            sfx = m.group(2) or ""
            out.append(f"{m.group(1)}{SUFFIX_TO_SEX.get(sfx, sfx)}")
        else:
            out.append(str(c))
    return out

def hex_to_rgba(hex_color, alpha=0.25):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

# Pre-computed color cache — no repeated MD5 hashing at render time
_COLOR_CACHE: dict[str, str] = {}
def stable_color(label: str) -> str:
    if label not in _COLOR_CACHE:
        _COLOR_CACHE[label] = PALETTE[
            int(hashlib.md5(label.encode()).hexdigest()[:8], 16) % len(PALETTE)
        ]
    return _COLOR_CACHE[label]

def shorten(lbl):
    return (
        lbl.replace(" (Bolivarian Republic of)", "")
           .replace(" (Democratic Republic of the)", " (DRC)")
           .replace("United States of America", "USA")
           .replace("United Kingdom of Great Britain and Northern Ireland", "UK")
           .replace("United Kingdom", "UK")
           .replace("China, Hong Kong SAR", "Hong Kong")
           .replace("China, Taiwan Province of China", "Taiwan")
    )

# Pre-computed ISO3 lookup — pycountry.lookup is slow; call it once per name
_ISO3_CACHE: dict[str, str | None] = {}
def to_iso3(name: str) -> str | None:
    if name not in _ISO3_CACHE:
        if name in MANUAL_ISO3:
            _ISO3_CACHE[name] = MANUAL_ISO3[name]
        else:
            try:
                _ISO3_CACHE[name] = pycountry.countries.lookup(name).alpha_3
            except LookupError:
                _ISO3_CACHE[name] = None
    return _ISO3_CACHE[name]

def norm_country(name):
    return COUNTRY_NAME_MAP.get(name, name)

def plotly_name(name):
    return PLOTLY_NAME_MAP.get(name, name)

# ── Load migration data ───────────────────────────────────────────────────────

xls = pd.ExcelFile(FILE_PATH)
df  = pd.read_excel(xls, sheet_name="Table 1", header=10).dropna(how="all")
df.columns = rename_year_cols([clean_col(c) for c in df.columns])

id_cols   = [c for c in ID_COLS if c in df.columns]
year_cols = [c for c in df.columns if c.split("_")[0] in BASE_YEARS]

df_long = df.melt(
    id_vars=id_cols, value_vars=year_cols,
    var_name="year_sex", value_name="migrant_stock",
)
df_long["migrant_stock"] = pd.to_numeric(df_long["migrant_stock"], errors="coerce")

excl_pat = "|".join(EXCLUDE_KEYWORDS)
df_long = df_long[
    ~df_long[dest_col].str.contains(excl_pat, na=False, case=False) &
    ~df_long[origin_col].str.contains(excl_pat, na=False, case=False)
]

split = df_long["year_sex"].str.split("_", n=1, expand=True)
df_long["year"] = split[0].str.extract(r"(\d{4})").astype(float)
df_long["sex"]  = split[1].str.strip().str.lower().map(
    {"total": "total", "male": "male", "female": "female"}
)
df_long = df_long.dropna(subset=["year", "migrant_stock"])

for col in [dest_col, origin_col]:
    df_long[col] = df_long[col].str.replace(r"\*$", "", regex=True).str.strip()

print(f"Loaded: {len(df_long):,} rows | "
      f"{df_long[origin_col].nunique()} origins | "
      f"{df_long[dest_col].nunique()} destinations")

# ── Load population data (World Bank) ────────────────────────────────────────

pop_raw = wb.data.DataFrame(
    "SP.POP.TOTL",
    time=[1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024],
    skipBlanks=True, columns="series",
).reset_index()
pop_raw.columns.name = None
pop_raw = pop_raw.rename(columns={
    "economy":     "iso3",
    "time":        "year",
    "SP.POP.TOTL": "population",
})
pop_raw["year"] = pop_raw["year"].str.replace("YR", "").astype(float)

wb_meta = wb.economy.DataFrame().reset_index()
wb_meta = wb_meta.rename(columns={wb_meta.columns[0]: "iso3", wb_meta.columns[1]: "wb_name"})
wb_meta = wb_meta[["iso3", "wb_name"]]
pop_raw = pop_raw.merge(wb_meta, on="iso3", how="left")

wb_to_un = {v: k for k, v in UN_TO_WB.items()}
pop_raw["origin"] = pop_raw["wb_name"].map(lambda n: wb_to_un.get(n, n))
pop = pop_raw[["origin", "year", "population"]].dropna()
print(f"Population loaded: {len(pop):,} rows, {pop['origin'].nunique()} countries")

# ── Merge population ──────────────────────────────────────────────────────────

df_long = df_long.merge(
    pop.rename(columns={"origin": origin_col}),
    on=[origin_col, "year"], how="left",
)
df_long["emigration_rate"] = df_long["migrant_stock"] / df_long["population"]

# ── Pre-compute per-year/sex slices (key speedup) ────────────────────────────
# Store sliced DataFrames keyed by (year, sex) so callbacks don't re-scan
# the full 1M+ row DataFrame on every interaction.

_SLICES: dict[tuple, pd.DataFrame] = {}

def get_slice(year: float, sex: str) -> pd.DataFrame:
    key = (year, sex)
    if key not in _SLICES:
        _SLICES[key] = df_long[
            (df_long["year"] == year) & (df_long["sex"] == sex)
        ].copy()
    return _SLICES[key]

# Warm the most-used slices at startup
for _yr in [float(y) for y in [1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024]]:
    for _sx in ["total", "male", "female"]:
        get_slice(_yr, _sx)

print("Slices pre-warmed.")

# ── Pre-compute choropleth aggregations ──────────────────────────────────────
# Choropleth redraws are the heaviest operation; pre-aggregate everything.

_CHORO_CACHE: dict[tuple, pd.DataFrame] = {}

def _build_choro_agg(year: float, sex: str, mode: str) -> pd.DataFrame:
    key = (year, sex, mode)
    if key in _CHORO_CACHE:
        return _CHORO_CACHE[key]

    d = get_slice(year, sex)

    if mode == "stock":
        agg = (
            d.groupby(dest_col)["migrant_stock"].sum()
             .reset_index()
             .rename(columns={dest_col: "country", "migrant_stock": "z"})
        )
    elif mode == "net":
        inf = d.groupby(dest_col)["migrant_stock"].sum().rename("inflow")
        out = d.groupby(origin_col)["migrant_stock"].sum().rename("outflow")
        net = pd.concat([inf, out], axis=1).fillna(0)
        net["z"] = net["inflow"] - net["outflow"]
        agg = net.reset_index()
        agg.columns = ["country", "inflow", "outflow", "z"]
    elif mode == "rate":
        agg = (
            d.groupby(origin_col)
             .agg(total_emigrants=("migrant_stock", "sum"),
                  population=("population", "first"))
             .assign(z=lambda d: d["total_emigrants"] / d["population"] * 100)
             .reset_index()
             .rename(columns={origin_col: "country"})
        )

    # Resolve ISO3 once per aggregation (cached inside to_iso3)
    agg["loc"] = agg["country"].map(plotly_name).map(to_iso3)
    _CHORO_CACHE[key] = agg
    return agg

# Warm all choropleth combinations at startup
for _yr in [float(y) for y in [1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024]]:
    for _sx in ["total", "male", "female"]:
        for _mode in ["stock", "net", "rate"]:
            _build_choro_agg(_yr, _sx, _mode)

print("Choropleth cache warm.")

# ── App setup ─────────────────────────────────────────────────────────────────

app    = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

years     = sorted(int(y) for y in df_long["year"].dropna().unique())
countries = sorted(df_long[origin_col].dropna().unique())
sexes     = sorted(df_long["sex"].dropna().unique())

FONT    = "Inter, Arial, sans-serif"
BG      = "#F0F2F5"
CARD    = "#FFFFFF"
CARD_BG = "#F8F9FA"

TAB_STYLE     = {"fontSize": "13px", "fontFamily": FONT, "padding": "9px 18px"}
SEL_TAB_STYLE = {**TAB_STYLE, "fontWeight": "700",
                 "borderTop": "3px solid #457B9D", "color": "#1a1a2e"}
GRAPH_CFG = {"displayModeBar": False}

# ── Layout ────────────────────────────────────────────────────────────────────

app.layout = html.Div([

    html.Div([
        html.H2("🌍 Global Migration Flow Explorer", style={
            "fontFamily": FONT, "margin": "0 0 4px 0",
            "color": "#1a1a2e", "fontSize": "18px",
        }),
        html.P(
            "Explore international migrant stocks using UN DESA 2024 data. "
            "A migrant is defined here as anyone living outside their country of birth, "
            "regardless of when they moved or why — this includes economic migrants, "
            "refugees, students, and long-term residents. "
            "Select an origin country and year to see where its emigrants settled, "
            "how flows have changed since 1990, and how it compares globally.",
            style={"margin": "0 0 6px 0", "color": "#555", "fontSize": "13px",
                   "maxWidth": "860px", "lineHeight": "1.5"},
        ),
        html.Div([
            html.Span("📊 Data: ", style={"fontWeight": "600", "fontSize": "12px"}),
            html.A(
                "UN DESA International Migrant Stock 2024",
                href="https://www.un.org/development/desa/pd/content/international-migrant-stock",
                target="_blank",
                style={"fontSize": "12px", "color": "#457B9D"},
            ),
            html.Span(
                " · Figures represent migrant stock (not annual flows) · "
                "Some countries may have limited data availability.",
                style={"fontSize": "12px", "color": "#888"},
            ),
        ]),
    ], style={
        "background": CARD, "borderBottom": "1px solid #DDD",
        "padding": "14px 24px 12px", "fontFamily": FONT,
    }),

    html.Div([
        html.Div([
            html.Label("Origin Country", id="country-label", style={
                "fontWeight": "600", "fontSize": "12px",
                "display": "block", "marginBottom": "3px",
            }),
            dcc.Dropdown(
                id="country",
                options=[{"label": c, "value": c} for c in countries],
                value="Italy" if "Italy" in countries else countries[0],
                clearable=False, style={"fontSize": "13px"},
            ),
        ], style={"flex": "2", "minWidth": "160px"}),

        html.Div([
            html.Label("Sex", style={
                "fontWeight": "600", "fontSize": "12px",
                "display": "block", "marginBottom": "3px",
            }),
            dcc.Dropdown(
                id="sex",
                options=[{"label": s.title(), "value": s} for s in sexes],
                value="total", clearable=False, style={"fontSize": "13px"},
            ),
        ], style={"flex": "1", "minWidth": "110px"}),

        html.Div([
            html.Label("Year", style={
                "fontWeight": "600", "fontSize": "12px",
                "display": "block", "marginBottom": "3px",
            }),
            dcc.Slider(
                id="year", min=min(years), max=max(years), step=None,
                value=max(years),
                marks={y: {"label": str(y), "style": {"fontSize": "11px"}}
                       for y in years},
                included=False,
            ),
        ], style={"flex": "3", "minWidth": "260px"}),

        html.Div([
            html.Button("▶ Play", id="play", n_clicks=0, style={
                "background": "#457B9D", "color": "#FFF", "border": "none",
                "borderRadius": "6px", "padding": "8px 20px",
                "fontSize": "13px", "cursor": "pointer",
                "fontWeight": "600", "marginTop": "18px",
            }),
        ]),

        dcc.Interval(id="interval", interval=1400, disabled=True),
        dcc.Store(id="playing",      data=False),
        dcc.Store(id="clicked-dest", data=None),

    ], style={
        "display": "flex", "gap": "14px", "alignItems": "flex-start",
        "flexWrap": "wrap", "background": CARD, "borderRadius": "10px",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.07)",
        "padding": "16px 20px", "margin": "14px",
    }),

    html.Div([
        dcc.Tabs(id="tabs", value="tab-sankey", style={"fontFamily": FONT}, children=[
            dcc.Tab(label="🔀  Sankey Flows", value="tab-sankey",
                    style=TAB_STYLE, selected_style=SEL_TAB_STYLE),
            dcc.Tab(label="🗺️  World Map",    value="tab-map",
                    style=TAB_STYLE, selected_style=SEL_TAB_STYLE),
            dcc.Tab(label="📈  Time Series",  value="tab-ts",
                    style=TAB_STYLE, selected_style=SEL_TAB_STYLE),
            dcc.Tab(label="🔥  Heatmap",      value="tab-heat",
                    style=TAB_STYLE, selected_style=SEL_TAB_STYLE),
            dcc.Tab(label="🏅  Bump Chart",   value="tab-bump",
                    style=TAB_STYLE, selected_style=SEL_TAB_STYLE),
        ]),
    ], style={"margin": "0 14px"}),

    html.Div(id="tab-content",  style={"margin": "14px"}),
    html.Div(id="detail-panel", style={"margin": "0 14px 14px"}),

], style={"margin": "0", "background": BG, "minHeight": "100vh", "fontFamily": FONT})

# ── Chart builders ────────────────────────────────────────────────────────────

def _empty(msg="No data for this selection"):
    f = go.Figure()
    f.update_layout(
        annotations=[dict(
            text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(size=14, color="#999"),
        )],
        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return f


def build_sankey(data: pd.DataFrame, origin_country: str) -> go.Figure:
    flow = (
        data.groupby([origin_col, dest_col])["migrant_stock"]
            .sum().reset_index()
            .pipe(lambda d: d[d["migrant_stock"] > 0])
            .sort_values("migrant_stock", ascending=False)
            .head(20)
    )
    if flow.empty:
        return _empty(f"No outflows found for {origin_country}")

    nodes       = pd.Index(pd.concat([flow[origin_col], flow[dest_col]]).unique())
    idx_map     = {n: i for i, n in enumerate(nodes)}
    node_colors = [stable_color(n) for n in nodes]
    link_colors = [hex_to_rgba(node_colors[idx_map[s]]) for s in flow[origin_col]]

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=18, thickness=20,
            label=[shorten(n) for n in nodes],
            color=node_colors,
            customdata=list(nodes),
            hovertemplate="<b>%{label}</b><extra></extra>",
            line=dict(color="white", width=0.5),
        ),
        link=dict(
            source=flow[origin_col].map(idx_map).tolist(),
            target=flow[dest_col].map(idx_map).tolist(),
            value=flow["migrant_stock"].tolist(),
            color=link_colors,
            hovertemplate=(
                "<b>%{source.label}</b> → <b>%{target.label}</b><br>"
                "%{value:,.0f} migrants<extra></extra>"
            ),
        ),
    ))
    fig.update_layout(
        title=dict(text=f"Emigration flows from <b>{origin_country}</b>",
                   font=dict(size=15, color="#222"), x=0.01),
        font=dict(family=FONT, size=13, color="#333"),
        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        height=600, margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


def build_bar(data: pd.DataFrame, origin_country: str) -> go.Figure:
    flow = (
        data.groupby(dest_col)["migrant_stock"].sum()
            .reset_index()
            .sort_values("migrant_stock", ascending=False)
            .head(10)
            .pipe(lambda d: d[d["migrant_stock"] > 0])
    )
    if flow.empty:
        return _empty()

    fig = go.Figure(go.Bar(
        x=flow["migrant_stock"],
        y=flow[dest_col].map(shorten),
        orientation="h",
        marker_color=[stable_color(c) for c in flow[dest_col]],
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} migrants<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Top 10 destinations from <b>{shorten(origin_country)}</b>",
                   font=dict(size=13, color="#222"), x=0.01),
        xaxis=dict(title="Migrant stock", tickformat=","),
        yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
        font=dict(family=FONT, size=12, color="#333"),
        paper_bgcolor=CARD_BG, plot_bgcolor="#FFFFFF",
        height=340, margin=dict(l=10, r=20, t=45, b=40),
    )
    return fig


def build_sankey_inbound(data: pd.DataFrame, dest_country: str) -> go.Figure:
    flow = (
        data.groupby([origin_col, dest_col])["migrant_stock"]
            .sum().reset_index()
            .pipe(lambda d: d[d["migrant_stock"] > 0])
            .sort_values("migrant_stock", ascending=False)
            .head(15)
    )
    if flow.empty:
        return _empty(f"No inflows found for {dest_country}")

    nodes       = pd.Index(pd.concat([flow[origin_col], flow[dest_col]]).unique())
    idx_map     = {n: i for i, n in enumerate(nodes)}
    node_colors = [stable_color(n) for n in nodes]
    link_colors = [hex_to_rgba(node_colors[idx_map[s]]) for s in flow[origin_col]]

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=25, thickness=20,
            label=[shorten(n) for n in nodes],
            color=node_colors,
            customdata=list(nodes),
            hovertemplate="<b>%{label}</b><extra></extra>",
            line=dict(color="white", width=0.5),
        ),
        link=dict(
            source=flow[origin_col].map(idx_map).tolist(),
            target=flow[dest_col].map(idx_map).tolist(),
            value=flow["migrant_stock"].tolist(),
            color=link_colors,
            hovertemplate=(
                "<b>%{source.label}</b> → <b>%{target.label}</b><br>"
                "%{value:,.0f} migrants<extra></extra>"
            ),
        ),
    ))
    fig.update_layout(
        title=dict(text=f"Immigration flows into <b>{dest_country}</b>",
                   font=dict(size=15, color="#222"), x=0.01),
        font=dict(family=FONT, size=13, color="#333"),
        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        height=480, margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


def build_bar_inbound(data: pd.DataFrame, dest_country: str) -> go.Figure:
    flow = (
        data.groupby(origin_col)["migrant_stock"].sum()
            .reset_index()
            .sort_values("migrant_stock", ascending=False)
            .head(15)
            .pipe(lambda d: d[d["migrant_stock"] > 0])
    )
    if flow.empty:
        return _empty()

    fig = go.Figure(go.Bar(
        x=flow["migrant_stock"],
        y=flow[origin_col].map(shorten),
        orientation="h",
        marker_color=[stable_color(c) for c in flow[origin_col]],
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} migrants<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Top 15 origins into <b>{shorten(dest_country)}</b>",
                   font=dict(size=13, color="#222"), x=0.01),
        xaxis=dict(title="Migrant stock", tickformat=","),
        yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
        font=dict(family=FONT, size=12, color="#333"),
        paper_bgcolor=CARD_BG, plot_bgcolor="#FFFFFF",
        height=500, margin=dict(l=10, r=20, t=45, b=40),
    )
    return fig


def build_choropleth(year: float, sex: str, mode: str = "stock") -> go.Figure:
    agg = _build_choro_agg(year, sex, mode)

    cfg = {
        "stock": ("Blues",  None, "Migrants",    f"Migrant Stock by Destination ({int(year)}, {sex})"),
        "net":   ("RdBu",   0,    "Net migrants", f"Net Migration — inflows minus outflows ({int(year)}, {sex})"),
        "rate":  ("OrRd",   None, "% abroad",     f"Emigration Rate — % of population living abroad ({int(year)}, {sex})"),
    }
    cscale, zmid, cb_title, title = cfg[mode]

    fig = go.Figure(go.Choropleth(
        locations=agg["loc"], locationmode="ISO-3",
        z=agg["z"], text=agg["country"],
        colorscale=cscale, zmid=zmid,
        colorbar=dict(title=cb_title, tickformat=","),
        hovertemplate="<b>%{text}</b><br>%{z:,.1f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#222"), x=0.01),
        geo=dict(
            showframe=False, showcoastlines=True,
            coastlinecolor="#AAAAAA", bgcolor=CARD_BG,
            landcolor="#F0F0F0", showland=True,
            oceancolor="#D0E8F0", showocean=True,
        ),
        paper_bgcolor=CARD_BG,
        font=dict(family=FONT, size=12, color="#333"),
        height=520, margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


def build_timeseries(origin_country: str, sex: str) -> go.Figure:
    # Use only the rows for this origin across all years — much smaller scan
    d = df_long[
        (df_long[origin_col] == origin_country) & (df_long["sex"] == sex)
    ]
    if d.empty:
        return _empty()

    total = d.groupby("year")["migrant_stock"].sum().reset_index()
    latest_yr = d["year"].max()
    top5 = (
        d[d["year"] == latest_yr]
        .groupby(dest_col)["migrant_stock"].sum()
        .sort_values(ascending=False).head(5).index.tolist()
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=total["year"], y=total["migrant_stock"],
        name="Total (all destinations)",
        mode="lines+markers",
        line=dict(color="#1a1a2e", width=3, dash="dash"),
        hovertemplate="Year %{x}: %{y:,.0f}<extra>Total</extra>",
    ))
    for i, dest in enumerate(top5):
        sub = (
            d[d[dest_col] == dest]
            .groupby("year")["migrant_stock"].sum().reset_index()
        )
        fig.add_trace(go.Scatter(
            x=sub["year"], y=sub["migrant_stock"],
            name=shorten(dest), mode="lines+markers",
            line=dict(color=PALETTE[i % len(PALETTE)], width=2),
            hovertemplate=(
                f"<b>{shorten(dest)}</b><br>"
                "Year %{x}: %{y:,.0f}<extra></extra>"
            ),
        ))
    fig.update_layout(
        title=dict(text=f"Emigration from <b>{origin_country}</b> over time ({sex})",
                   font=dict(size=14, color="#222"), x=0.01),
        xaxis=dict(title="Year", tickmode="array", tickvals=years, tickformat="d"),
        yaxis=dict(title="Migrant stock", tickformat=","),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.85)",
                    font=dict(size=11)),
        font=dict(family=FONT, size=12, color="#333"),
        paper_bgcolor=CARD_BG, plot_bgcolor="#FFFFFF",
        height=480, margin=dict(l=10, r=10, t=50, b=40),
    )
    return fig


def build_heatmap(origin_country: str, sex: str, top_n: int = 15) -> go.Figure:
    d = df_long[
        (df_long[origin_col] == origin_country) & (df_long["sex"] == sex)
    ].copy()
    d["migrant_stock"] = pd.to_numeric(d["migrant_stock"], errors="coerce")
    d = d.dropna(subset=["migrant_stock"])

    if d.empty:
        return _empty(f"No data for {origin_country}")

    pivot = (
        d.groupby(["year", dest_col])["migrant_stock"]
         .sum().unstack(fill_value=0)
    )
    top_dests = pivot.sum().nlargest(top_n).index
    pivot     = pivot[top_dests]

    fig = go.Figure(go.Heatmap(
        z=np.log1p(pivot.values),
        x=[shorten(c) for c in pivot.columns],
        y=pivot.index.astype(int).astype(str),
        colorscale="YlOrRd",
        colorbar=dict(title="log(migrants+1)", tickformat=".1f"),
        customdata=pivot.values,
        hovertemplate=(
            "Destination: <b>%{x}</b><br>"
            "Year: %{y}<br>"
            "%{customdata:,.0f} migrants<extra></extra>"
        ),
    ))
    fig.update_layout(
        title=dict(
            text=(f"Emigration from <b>{origin_country}</b> — "
                  f"Top {top_n} destinations over time ({sex})"),
            font=dict(size=13, color="#222"), x=0.01,
        ),
        xaxis=dict(tickfont=dict(size=9), tickangle=-40, title="Destination"),
        yaxis=dict(tickfont=dict(size=9), title="Year"),
        font=dict(family=FONT, size=11, color="#333"),
        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        height=500, margin=dict(l=60, r=10, t=50, b=150),
    )
    return fig


def build_bump(origin_country: str, sex: str, top_n: int = 10) -> go.Figure:
    d = df_long[(df_long[origin_col] == origin_country) & (df_long["sex"] == sex)]
    if d.empty:
        return _empty()

    latest_yr = d["year"].max()
    top_dests = (
        d[d["year"] == latest_yr]
        .groupby(dest_col)["migrant_stock"].sum()
        .sort_values(ascending=False).head(top_n).index.tolist()
    )

    # Vectorised rank computation — avoid per-year Python loop
    ranked_all = (
        d.groupby(["year", dest_col])["migrant_stock"].sum()
         .groupby(level="year", group_keys=False)
         .rank(ascending=False, method="min")
         .reset_index()
    )
    ranked_all.columns = ["year", "dest", "rank"]
    ranks_df = ranked_all[ranked_all["dest"].isin(top_dests)]

    if ranks_df.empty:
        return _empty()

    fig = go.Figure()
    for i, dest in enumerate(top_dests):
        sub   = ranks_df[ranks_df["dest"] == dest].sort_values("year")
        color = PALETTE[i % len(PALETTE)]
        fig.add_trace(go.Scatter(
            x=sub["year"], y=sub["rank"],
            mode="lines+markers",
            name=shorten(dest),
            line=dict(color=color, width=2.5),
            marker=dict(size=10, color=color),
            text=sub["rank"].astype(str),
            textposition="top center",
            textfont=dict(size=9, color=color),
            hovertemplate=(
                f"<b>{shorten(dest)}</b><br>"
                "Year: %{x}<br>Rank: %{y}<extra></extra>"
            ),
        ))
    fig.update_layout(
        title=dict(text=f"Top Destination Ranks from <b>{origin_country}</b> ({sex})",
                   font=dict(size=14, color="#222"), x=0.01),
        xaxis=dict(
            title="Year", tickmode="array",
            tickvals=years, ticktext=[str(y) for y in years],
            showgrid=True, gridcolor="#EEE",
        ),
        yaxis=dict(
            title="Rank (1 = largest)", autorange="reversed",
            tickmode="linear", tick0=5, dtick=5,
            range=[0.5, top_n + 0.5],
            showgrid=False, gridcolor="#EEE",
        ),
        legend=dict(x=1.01, y=1, font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        font=dict(family=FONT, size=12, color="#333"),
        paper_bgcolor=CARD_BG, plot_bgcolor="#FFFFFF",
        height=650, margin=dict(l=10, r=140, t=50, b=40),
    )
    return fig


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(
    Output("tab-content", "children"),
    Input("tabs",    "value"),
    Input("year",    "value"),
    Input("country", "value"),
    Input("sex",     "value"),
)
def render_tab(tab, year, country, sex):
    try:
        year = float(year)
        sl   = get_slice(year, sex)   # fast cached slice

        if tab == "tab-sankey":
            filt_out = sl[sl[origin_col] == country]
            filt_in  = sl[sl[dest_col]   == country]
            return html.Div([
                dcc.RadioItems(
                    id="flow-dir",
                    options=[
                        {"label": "  Emigrants — where do people from here go?", "value": "out"},
                        {"label": "  Immigrants — where do people here come from?", "value": "in"},
                    ],
                    value="out",
                    labelStyle={"display": "inline-block", "marginRight": "20px"},
                    style={"fontSize": "13px", "marginBottom": "12px"},
                ),
                dcc.Graph(id="sankey",    figure=build_sankey(filt_out, country), config=GRAPH_CFG),
                dcc.Graph(id="bar-top10", figure=build_bar(filt_out, country),    config=GRAPH_CFG,
                          style={"marginTop": "12px"}),
                html.P(
                    "💡 Click any node in the Sankey to see a corridor trend below.",
                    style={"color": "#777", "fontSize": "12px", "margin": "6px 4px 0"},
                ),
            ])

        if tab == "tab-map":
            return html.Div([
                html.Div([
                    html.Label("Map mode:", style={"fontWeight": "600", "fontSize": "12px"}),
                    dcc.RadioItems(
                        id="map-mode",
                        options=[
                            {"label": "  Migrant Stock (by destination)",          "value": "stock"},
                            {"label": "  Net Migration (inflows − outflows)",       "value": "net"},
                            {"label": "  Emigration Rate (% of population abroad)", "value": "rate"},
                        ],
                        value="stock",
                        labelStyle={"display": "block", "margin": "4px 0"},
                        style={"fontSize": "13px"},
                    ),
                ], style={
                    "background": CARD, "borderRadius": "8px",
                    "padding": "14px", "marginBottom": "12px",
                    "display": "inline-block",
                }),
                dcc.Graph(id="choropleth",
                          figure=build_choropleth(year, sex, "stock"),
                          config=GRAPH_CFG),
            ])

        if tab == "tab-ts":
            return dcc.Graph(id="timeseries",
                             figure=build_timeseries(country, sex),
                             config=GRAPH_CFG)

        if tab == "tab-heat":
            return html.Div([
                html.Div([
                    html.Label("Top N destinations:", style={
                        "fontWeight": "600", "fontSize": "12px",
                        "display": "block", "marginBottom": "6px",
                    }),
                    html.Div(
                        dcc.Slider(id="heat-n", min=5, max=25, step=5, value=15,
                                   marks={i: str(i) for i in range(5, 26, 5)},
                                   included=False),
                        style={"width": "260px"},
                    ),
                ], style={
                    "background": CARD, "borderRadius": "8px",
                    "padding": "14px", "marginBottom": "12px",
                    "display": "inline-block",
                }),
                dcc.Graph(id="heatmap",
                          figure=build_heatmap(country, sex, 15),
                          config=GRAPH_CFG),
            ])

        if tab == "tab-bump":
            return dcc.Graph(id="bump",
                             figure=build_bump(country, sex),
                             config=GRAPH_CFG)

        return html.Div("Select a tab.")

    except Exception as e:
        import traceback; traceback.print_exc()
        return html.Div(f"⚠️ Error rendering tab: {e}",
                        style={"color": "red", "padding": "20px", "fontFamily": FONT})


@app.callback(
    Output("clicked-dest", "data"),
    Input("sankey", "clickData"),
    prevent_initial_call=True,
)
def store_click(clickData):
    if not clickData:
        return None
    pt = clickData["points"][0]
    return pt.get("customdata") or pt.get("label")


@app.callback(
    Output("detail-panel", "children"),
    Input("clicked-dest", "data"),
    State("country", "value"),
    State("sex",     "value"),
    State("tabs",    "value"),
)
def update_detail(dest, origin, sex, tab):
    if not dest or tab != "tab-sankey":
        return None

    d = df_long[
        (df_long[origin_col] == origin) &
        (df_long[dest_col]   == dest)   &
        (df_long["sex"]      == sex)
    ].sort_values("year")

    if d.empty:
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d["year"], y=d["migrant_stock"],
        mode="lines+markers",
        line=dict(color="#0072B2", width=2.5),
        marker=dict(size=8, color="#0072B2"),
        fill="tozeroy", fillcolor="rgba(0,114,178,0.08)",
        hovertemplate="Year: %{x}<br>Stock: %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(
            text=f"📍 Corridor: <b>{shorten(origin)}</b> → <b>{shorten(dest)}</b>",
            font=dict(size=13, color="#1a1a2e"), x=0.01,
        ),
        xaxis=dict(title="Year", tickmode="array", tickvals=years, tickformat="d"),
        yaxis=dict(title="Migrant stock", tickformat=","),
        font=dict(family=FONT, size=12, color="#333"),
        paper_bgcolor=CARD, plot_bgcolor=CARD_BG,
        height=230, margin=dict(l=50, r=20, t=45, b=45),
    )
    return html.Div(
        dcc.Graph(figure=fig, config=GRAPH_CFG),
        style={
            "background": CARD, "borderRadius": "10px",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.07)", "padding": "4px",
        },
    )


@app.callback(
    Output("choropleth", "figure"),
    Input("map-mode", "value"),
    State("year", "value"),
    State("sex",  "value"),
    prevent_initial_call=True,
)
def update_choropleth(mode, year, sex):
    return build_choropleth(float(year), sex, mode)


@app.callback(
    Output("playing", "data"),
    Input("play", "n_clicks"),
    State("playing", "data"),
    prevent_initial_call=True,
)
def toggle_play(_, playing):
    return not playing


@app.callback(
    Output("interval", "disabled"),
    Input("playing", "data"),
)
def toggle_interval(playing):
    return not playing


@app.callback(
    Output("sankey",    "figure"),
    Output("bar-top10", "figure"),
    Input("flow-dir",   "value"),
    State("year",       "value"),
    State("country",    "value"),
    State("sex",        "value"),
    prevent_initial_call=True,
)
def update_flow_direction(direction, year, country, sex):
    sl = get_slice(float(year), sex)
    if direction == "out":
        filt = sl[sl[origin_col] == country]
        return build_sankey(filt, country), build_bar(filt, country)
    else:
        filt = sl[sl[dest_col] == country]
        return build_sankey_inbound(filt, country), build_bar_inbound(filt, country)


@app.callback(
    Output("country-label", "children"),
    Input("flow-dir", "value"),
    prevent_initial_call=True,
)
def update_country_label(direction):
    return "Destination Country" if direction == "in" else "Origin Country"


@app.callback(
    Output("year", "value"),
    Input("interval", "n_intervals"),
    State("year",    "value"),
    State("playing", "data"),
)
def animate(_, year, playing):
    if not playing:
        return year
    idx = years.index(int(year))
    return years[(idx + 1) % len(years)]


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)