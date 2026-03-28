"""
Senso Knowledge Base Ingest Script
Scrapes geopolitical intelligence from multiple sources using Firecrawl
and uploads to Senso for use by the Document and Conflict agents.

Run this BEFORE the demo to pre-populate the knowledge base.
Usage: python ingest_senso.py

Processes topics in batches of 20 to avoid timeouts.
~177 topics total, ~20-30 minutes to complete.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from firecrawl import FirecrawlApp

FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
SENSO_API_KEY = os.environ.get("SENSO_API_KEY", "")

firecrawl = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

BATCH_SIZE = 20
FIRECRAWL_LIMIT = 5
CONTENT_CHAR_LIMIT = 8000

# ─── Knowledge Base Topics ────────────────────────────────────────────────────

SCRAPE_TOPICS = [
    # ── Trump Term 1 (2017-2021) ──
    ("trump_fp_first_term",        "Trump foreign policy first term overview"),
    ("trump_iran_jcpoa_2018",      "Trump Iran nuclear deal withdrawal 2018"),
    ("trump_iran_soleimani_2020",  "Trump Iran Soleimani assassination January 2020"),
    ("trump_iran_max_pressure",    "Trump Iran sanctions maximum pressure"),
    ("trump_north_korea_summits",  "Trump North Korea Kim Jong Un summits"),
    ("trump_nato_burden_2017",     "Trump NATO burden sharing demands 2017 2018"),
    ("trump_russia_mueller",       "Trump Russia Mueller investigation"),
    ("trump_china_trade_2018",     "Trump China trade war tariffs 2018 2019"),
    ("trump_syria_withdrawal_2019","Trump Syria withdrawal 2019"),
    ("trump_afghanistan_2020",     "Trump Afghanistan peace deal Taliban 2020"),
    ("trump_saudi_yemen",          "Trump Saudi Arabia arms deal Yemen"),
    ("trump_israel_abraham_accords","Trump Israel Palestine Abraham Accords"),
    ("trump_venezuela_maduro",     "Trump Venezuela Maduro sanctions"),
    ("trump_turkey_erdogan",       "Trump Turkey Erdogan relationship"),
    ("trump_paris_climate",        "Trump withdrawal Paris climate accord"),
    ("trump_who_covid",            "Trump WHO withdrawal COVID"),
    ("trump_ukraine_impeach_2019", "Trump impeachment Ukraine aid 2019"),

    # ── Trump Term 2 (2025-present) ──
    ("trump2_fp_2025",             "Trump second term foreign policy 2025"),
    ("trump2_iran_2025",           "Trump Iran war 2025"),
    ("trump2_nato_2025",           "Trump NATO 2025 relationships"),
    ("trump2_russia_ukraine_2025", "Trump Russia Ukraine negotiations 2025"),
    ("trump2_china_tariffs_2025",  "Trump China tariffs 2025"),
    ("trump2_greenland_2025",      "Trump Greenland acquisition attempt 2025"),
    ("trump2_panama_canal_2025",   "Trump Panama Canal 2025"),
    ("trump2_middle_east_2025",    "Trump Middle East policy 2025"),
    ("trump2_military_2025",       "Trump military deployments 2025"),
    ("rubio_iran_2025",            "Rubio Secretary of State Iran 2025"),
    ("trump2_sanctions_2025",      "Trump sanctions policy 2025"),
    ("trump2_israel_gaza_2025",    "Trump Israel Gaza 2025"),

    # ── Biden Term (2021-2025) ──
    ("biden_fp_overview",          "Biden foreign policy overview"),
    ("biden_afghanistan_2021",     "Biden Afghanistan withdrawal August 2021"),
    ("biden_ukraine_2022",         "Biden Ukraine Russia war support 2022"),
    ("biden_china_taiwan",         "Biden China Taiwan policy"),
    ("biden_iran_jcpoa",           "Biden Iran nuclear negotiations JCPOA"),
    ("biden_saudi_khashoggi",      "Biden Saudi Arabia relationship Khashoggi"),
    ("biden_israel_gaza_oct7",     "Biden Israel Gaza October 7 response"),
    ("biden_nato_finland_sweden",  "Biden NATO expansion Finland Sweden"),
    ("biden_china_chips",          "Biden China chip export restrictions"),
    ("biden_climate_paris",        "Biden climate diplomacy Paris accord"),
    ("biden_north_korea",          "Biden North Korea policy"),
    ("biden_venezuela",            "Biden Venezuela sanctions"),
    ("biden_afghanistan_conseq",   "Biden withdrawal Afghanistan consequences"),

    # ── Obama Term (2009-2017) ──
    ("obama_fp_doctrine",          "Obama foreign policy doctrine overview"),
    ("obama_iran_jcpoa_2015",      "Obama Iran nuclear deal JCPOA 2015"),
    ("obama_ukraine_crimea_2014",  "Obama Russia Ukraine Crimea annexation 2014"),
    ("obama_syria_redline",        "Obama Syria red line chemical weapons"),
    ("obama_isis_iraq_syria",      "Obama ISIS Iraq Syria campaign"),
    ("obama_afghanistan_surge",    "Obama Afghanistan surge withdrawal"),
    ("obama_cuba_normalization",   "Obama Cuba normalization relations"),
    ("obama_pivot_asia",           "Obama pivot to Asia China policy"),
    ("obama_north_korea_patience", "Obama North Korea strategic patience"),
    ("obama_drone_strikes",        "Obama drone strikes Yemen Pakistan"),
    ("obama_nato_russia",          "Obama NATO Russia relations"),
    ("obama_arab_spring",          "Obama Arab Spring response"),
    ("obama_libya_gaddafi",        "Obama Libya intervention Gaddafi"),

    # ── Bush Term (2001-2009) ──
    ("bush_iraq_2003_wmd",         "Bush Iraq war 2003 WMD false intelligence"),
    ("bush_afghanistan_2001",      "Bush Afghanistan invasion 2001 Taliban"),
    ("bush_war_on_terror",         "Bush war on terror doctrine"),
    ("bush_iran_axis_evil",        "Bush Iran axis of evil"),
    ("bush_north_korea_six_party", "Bush North Korea nuclear six party talks"),
    ("bush_nato_expansion",        "Bush NATO expansion Eastern Europe"),
    ("bush_russia_georgia_2008",   "Bush Russia Georgia war 2008"),
    ("bush_katrina",               "Bush Hurricane Katrina government response"),
    ("bush_financial_crisis_2008", "Bush financial crisis 2008 response"),

    # ── Clinton Term (1993-2001) ──
    ("clinton_kosovo_bosnia",      "Clinton Kosovo Bosnia NATO intervention"),
    ("clinton_iraq_sanctions",     "Clinton Iraq sanctions Saddam Hussein"),
    ("clinton_north_korea_1994",   "Clinton North Korea nuclear agreement 1994"),
    ("clinton_china_wto",          "Clinton China trade relations WTO"),
    ("clinton_somalia_blackhawk",  "Clinton Somalia Black Hawk Down"),

    # ── Iran ──
    ("iran_us_war_2025",           "Iran US war 2025 latest"),
    ("iran_nuclear_2025",          "Iran nuclear program enrichment 2025"),
    ("iran_proxies_2025",          "Iran proxy forces Middle East 2025"),
    ("iran_houthi_red_sea_2025",   "Iran Houthi Red Sea attacks 2025"),
    ("iran_hezbollah_2025",        "Iran Hezbollah Lebanon 2025"),
    ("iran_israel_shadow_war",     "Iran Israel shadow war 2025"),
    ("hormuz_tensions_2025",       "Strait of Hormuz military tensions 2025"),
    ("iran_oil_sanctions_2025",    "Iran oil exports sanctions 2025"),

    # ── Ukraine Russia ──
    ("ukraine_russia_war_2025",    "Ukraine Russia war 2025 latest"),
    ("ukraine_ceasefire_2025",     "Ukraine ceasefire negotiations 2025"),
    ("russia_advances_2025",       "Russia military advances Ukraine 2025"),
    ("ukraine_us_aid_2025",        "Ukraine US military aid 2025"),
    ("nato_ukraine_member_2025",   "NATO Ukraine membership debate 2025"),
    ("russia_nuclear_threats_2025","Russia nuclear threats 2025"),
    ("ukraine_zelensky_trump",     "Ukraine Zelensky Trump negotiations"),
    ("russia_economy_sanct_2025",  "Russia economy sanctions impact 2025"),

    # ── Israel Gaza ──
    ("gaza_war_2025",              "Gaza war 2025 latest ceasefire"),
    ("israel_hamas_negot_2025",    "Israel Hamas negotiations 2025"),
    ("gaza_humanitarian_2025",     "Gaza humanitarian crisis 2025"),
    ("west_bank_settlements_2025", "West Bank settlements 2025"),
    ("israel_iran_conflict_2025",  "Israel Iran direct conflict 2025"),
    ("two_state_solution_2025",    "Two state solution status 2025"),

    # ── China Taiwan ──
    ("china_taiwan_tensions_2025", "China Taiwan military tensions 2025"),
    ("taiwan_strait_incidents_2025","Taiwan Strait incidents 2025"),
    ("china_taiwan_exercises_2025","China military exercises Taiwan 2025"),
    ("us_taiwan_relations_act",    "US Taiwan Relations Act defense"),
    ("taiwan_semiconductors",      "China Taiwan semiconductor industry"),
    ("taiwan_independence_2025",   "Taiwan independence movement 2025"),

    # ── China US ──
    ("us_china_trade_2025",        "US China trade war 2025"),
    ("china_us_military_comp",     "China US military competition"),
    ("south_china_sea_2025",       "South China Sea disputes 2025"),
    ("china_belt_road_2025",       "China Belt Road Initiative 2025"),
    ("us_china_tech_semicon",      "US China technology war semiconductors"),
    ("china_economy_2025",         "China economy slowdown 2025"),
    ("china_russia_alliance_2025", "China Russia alliance 2025"),

    # ── North Korea ──
    ("north_korea_nuclear_2025",   "North Korea nuclear tests 2025"),
    ("north_korea_russia_2025",    "North Korea Russia military cooperation"),
    ("kim_jong_un_2025",           "Kim Jong Un latest actions 2025"),
    ("north_korea_missiles_2025",  "North Korea missiles launches 2025"),
    ("north_korea_us_diplomacy",   "North Korea US diplomacy status"),

    # ── Middle East Broader ──
    ("saudi_vision_2030",          "Saudi Arabia Vision 2030 2025"),
    ("saudi_iran_normalization",   "Saudi Arabia Iran normalization"),
    ("yemen_war_2025",             "Yemen war 2025 status"),
    ("syria_post_assad_2025",      "Syria Assad fall aftermath 2025"),
    ("turkey_nato_2025",           "Turkey NATO relationship 2025"),
    ("iraq_us_military_2025",      "Iraq US military presence 2025"),

    # ── Africa ──
    ("sudan_civil_war_2025",       "Sudan civil war 2025"),
    ("sahel_coups_2025",           "Sahel coups military governments 2025"),
    ("africa_china_influence_2025","Africa China influence 2025"),
    ("somalia_alshabaab_2025",     "Somalia al-Shabaab 2025"),

    # ── Latin America ──
    ("venezuela_maduro_2025",      "Venezuela Maduro 2025"),
    ("mexico_cartel_us",           "Mexico cartel US relations"),
    ("cuba_us_2025",               "Cuba US relations 2025"),

    # ── How Wars Start ──
    ("war_escalation_patterns",    "How wars escalate from tensions historical patterns"),
    ("sanctions_lead_to_war",      "Economic sanctions lead to war historical examples"),
    ("military_buildup_warning",   "Military buildup warning signs before conflict"),
    ("assassination_war_escalation","Assassination political leaders war escalation history"),
    ("naval_blockades_war",        "Naval blockades war triggers history"),
    ("false_flag_operations",      "False flag operations history wars"),
    ("proxy_wars_cold_war",        "Proxy wars superpowers Cold War history"),

    # ── How Conflicts End ──
    ("peace_negotiations_history", "Peace negotiations successful history patterns"),
    ("ceasefire_history",          "Ceasefire agreements history success failure"),
    ("war_exhaustion_peace",       "War exhaustion peace settlements"),
    ("international_mediation",    "International mediation conflict resolution examples"),
    ("postwar_reconstruction",     "Economic reconstruction post war history"),

    # ── Propaganda and Information War ──
    ("state_media_propaganda",     "State media propaganda techniques history"),
    ("wartime_disinformation",     "Wartime disinformation campaigns history"),
    ("social_media_war_narratives","Social media war narratives manipulation"),
    ("intelligence_false_info",    "Intelligence agencies false information history"),
    ("wmd_iraq_propaganda",        "WMD Iraq propaganda lessons"),
    ("information_warfare",        "Information warfare modern conflicts"),

    # ── Source Credibility — Western Media ──
    ("source_reuters",             "Reuters news agency accuracy credibility"),
    ("source_ap",                  "Associated Press AP news credibility"),
    ("source_bbc",                 "BBC news accuracy political bias"),
    ("source_cnn",                 "CNN credibility accuracy record"),
    ("source_nytimes",             "New York Times accuracy record"),
    ("source_wapo",                "Washington Post credibility"),
    ("source_axios",               "Axios news reliability"),
    ("source_cnbc",                "CNBC financial news accuracy"),
    ("source_foxnews",             "Fox News accuracy credibility bias"),
    ("source_npr",                 "NPR credibility accuracy"),

    # ── Source Credibility — State Media ──
    ("source_rt_russia",           "RT Russia Today propaganda bias"),
    ("source_xinhua",              "Xinhua China state media credibility"),
    ("source_presstv_iran",        "Iran Press TV bias credibility"),
    ("source_cgtn",                "CGTN China Global Television bias"),
    ("source_alarabiya",           "Al Arabiya Saudi bias"),
    ("source_presstv2",            "Press TV Iran propaganda"),

    # ── Source Credibility — Independent/Regional ──
    ("source_aljazeera",           "Al Jazeera Qatar bias credibility"),
    ("source_almonitor",           "Al Monitor Middle East credibility"),
    ("source_haaretz",             "Haaretz Israel news credibility"),
    ("source_dawn_pakistan",       "Dawn Pakistan news credibility"),
    ("source_guardian",            "The Guardian accuracy credibility"),

    # ── US Constitutional Law ──
    ("war_powers_resolution_1973",    "War Powers Resolution 1973 presidential limits 60 day rule"),
    ("article_ii_commander_chief",    "Article II commander in chief powers scope limits"),
    ("article_i_war_powers_congress", "Article I congressional war declaration authority history"),
    ("ieepa_sanctions_authority",     "IEEPA International Emergency Economic Powers Act presidential authority sanctions"),
    ("aumf_2001_scope",               "AUMF 2001 Authorization Use Military Force scope Al Qaeda"),
    ("aumf_2002_iraq",                "AUMF 2002 Iraq war authorization scope"),
    ("national_emergencies_act",      "National Emergencies Act presidential emergency powers"),
    ("executive_order_legal_limits",  "Executive order foreign policy constitutional legal limits"),
    ("presidential_sanctions_history","Presidential sanctions history legal authority statutory basis"),

    # ── Supreme Court Cases — Executive Power ──
    ("youngstown_1952",               "Youngstown Sheet Tube Sawyer 1952 ruling presidential war powers limits"),
    ("dames_moore_regan_1981",        "Dames Moore v Regan 1981 Iran assets presidential power ruling"),
    ("trump_v_hawaii_2018",           "Trump v Hawaii 2018 travel ban executive power ruling"),
    ("zivotofsky_kerry_2015",         "Zivotofsky v Kerry 2015 presidential foreign affairs power"),
    ("curtiss_wright_1936",           "United States v Curtiss Wright 1936 broad foreign affairs presidential powers"),
    ("missouri_v_holland_1920",       "Missouri v Holland 1920 treaty powers supreme court ruling"),
    ("scotus_war_powers_cases",       "Supreme Court war powers presidential limits cases history"),
    ("hamdi_v_rumsfeld_2004",         "Hamdi v Rumsfeld 2004 enemy combatant due process ruling"),
    ("rasul_v_bush_2004",             "Rasul v Bush 2004 Guantanamo habeas corpus ruling"),

    # ── International Law ──
    ("un_charter_article_51",         "UN Charter Article 51 self defense requirements imminent threat"),
    ("un_charter_use_of_force",       "UN Charter use of force prohibition Article 2(4)"),
    ("geneva_conventions_military",   "Geneva Conventions military action requirements law of war"),
    ("icj_rulings_us",                "International Court of Justice rulings against United States"),
    ("nuclear_nonproliferation_treaty","Nuclear Non-Proliferation Treaty NPT obligations"),
    ("vienna_convention_diplomatic",  "Vienna Convention diplomatic immunity law"),
    ("nato_article_5_legal_trigger",  "NATO Article 5 collective defense legal trigger requirements"),
    ("jcpoa_legal_status",            "JCPOA Iran nuclear deal legal status withdrawal"),
    ("sanctions_international_law",   "Economic sanctions international law WTO limits legality"),
    ("icj_iran_us_1955_treaty",       "ICJ Iran US 1955 Treaty of Amity sanctions ruling"),

    # ── Historical Legal Precedents ──
    ("kosovo_clinton_no_authorization","Kosovo Clinton 1999 military action no UN authorization legal debate"),
    ("iraq_2003_legal_authority",     "Iraq war 2003 legal authority international law UN"),
    ("libya_2011_legal_basis",        "Libya intervention 2011 legal basis UN authorization"),
    ("syria_strikes_war_powers",      "Syria strikes Obama Trump legal authority War Powers Act"),
    ("soleimani_strike_legal",        "Iran Soleimani strike 2020 legal justification War Powers debate"),
    ("afghanistan_withdrawal_legal",  "Afghanistan withdrawal 2021 legal treaty congressional notification"),
    ("panama_invasion_1989_legal",    "Panama invasion 1989 legal justification"),
    ("grenada_invasion_legal",        "Grenada invasion 1983 legal authority"),

    # ── Congressional War Powers History ──
    ("congressional_war_declarations","Congressional war declarations history all US wars"),
    ("war_powers_invocations",        "War Powers Resolution invocations history presidents"),
    ("congressional_aumf_history",    "Congressional AUMF history all authorizations military force"),
    ("iran_war_powers_2020",          "Iran war powers Senate resolution 2020 Trump limits"),
    ("yemen_war_powers_congress",     "Yemen war powers congressional debate vote"),
    ("ukraine_aid_authorization",     "Ukraine military aid congressional authorization legal basis"),

    # ── Economic Economic Powers ──
    ("ofac_sanctions_legal",          "OFAC sanctions Treasury Department legal authority"),
    ("iran_sanctions_codified",       "Iran sanctions codified Congress CISADA CAATSA law"),
    ("russia_sanctions_legal_basis",  "Russia sanctions legal basis CAATSA statutory authority"),
    ("china_trade_section_301_232",   "China trade tariffs Section 301 232 presidential authority"),

    # ── Economic and Market Signals ──
    ("oil_price_conflict",         "Oil price spikes military conflict history"),
    ("gold_price_war",             "Gold price war uncertainty correlation"),
    ("stock_market_geopolitics",   "Stock market crashes geopolitical events"),
    ("crypto_war_sanctions",       "Crypto markets war sanctions correlation"),
    ("currency_collapse_sanctions","Currency collapse sanctions history"),
    ("sanctions_effectiveness",    "Economic sanctions effectiveness history"),
    ("trade_war_economic_impact",  "Trade war economic impact history"),
    ("commodity_prices_conflict",  "Commodity prices conflict impact"),

    # ── International Organizations ──
    ("un_security_council_veto",   "United Nations Security Council veto history"),
    ("un_peacekeeping",            "UN peacekeeping missions history"),
    ("nato_article5_history",      "NATO Article 5 history invocations"),
    ("iaea_inspections_history",   "IAEA nuclear inspections Iran history"),
    ("icc_cases",                  "ICC International Criminal Court cases"),
    ("world_bank_imf_crises",      "World Bank IMF crisis interventions"),
    ("g7_g20_sanctions",           "G7 G20 sanctions coordination"),
    ("opec_geopolitics",           "OPEC oil production geopolitical decisions"),
]


def scrape_topic(topic_key: str, search_query: str) -> list[dict]:
    """Scrape content for a topic using Firecrawl search."""
    print(f"  Scraping: {search_query[:60]}...")
    results = []

    try:
        search_result = firecrawl.search(search_query, limit=FIRECRAWL_LIMIT)
        items = getattr(search_result, 'web', None) or []
        for item in items:
            url = getattr(item, 'url', '')
            title = getattr(item, 'title', '')
            description = getattr(item, 'description', '')
            content = f"Title: {title}\n\n{description}" if description else title
            if content and len(content) > 50:
                results.append({
                    "url": url,
                    "content": content[:CONTENT_CHAR_LIMIT],
                    "topic": topic_key,
                })
    except Exception as e:
        print(f"    Warning: {e}")

    return results


def save_to_markdown(topic_key: str, items: list[dict], output_dir: Path) -> Path | None:
    """Save scraped content to a markdown file."""
    if not items:
        return None

    content = f"# {topic_key.replace('_', ' ').title()}\n\n"
    for item in items:
        content += f"## Source: {item['url']}\n\n{item['content']}\n\n---\n\n"

    filepath = output_dir / f"{topic_key}.md"
    filepath.write_text(content, encoding="utf-8")
    return filepath


def upload_to_senso(filepath: Path) -> bool:
    """Upload a file to Senso knowledge base."""
    try:
        result = subprocess.run(
            ["senso", "ingest", "upload", str(filepath)],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "SENSO_API_KEY": SENSO_API_KEY},
        )

        if result.returncode == 0:
            print(f"    ✓ Uploaded: {filepath.name}")
            return True
        else:
            output = (result.stdout + result.stderr).strip()
            # 422 = Senso duplicate detection — content already in KB
            if "422" in output:
                print(f"    ~ Already in KB: {filepath.name}")
                return True
            print(f"    ✗ Upload failed: {output[:150]}")
            return False
    except FileNotFoundError:
        print("    ✗ Senso CLI not found. Install: npm install -g @senso-ai/cli")
        return False
    except Exception as e:
        print(f"    ✗ Upload error: {e}")
        return False


def process_batch(batch: list[tuple[str, str]], batch_num: int, total_batches: int, output_dir: Path) -> tuple[int, int]:
    """Process a single batch of topics. Returns (uploaded, failed)."""
    uploaded = 0
    failed = 0
    print(f"\n{'─' * 60}")
    print(f"BATCH {batch_num}/{total_batches}  ({len(batch)} topics)")
    print(f"{'─' * 60}")

    for i, (topic_key, search_query) in enumerate(batch):
        global_idx = (batch_num - 1) * BATCH_SIZE + i + 1
        print(f"[{global_idx}/{len(SCRAPE_TOPICS)}] {topic_key}")

        items = scrape_topic(topic_key, search_query)
        if not items:
            print(f"  No content found, skipping")
            failed += 1
            continue

        filepath = save_to_markdown(topic_key, items, output_dir)
        if not filepath:
            failed += 1
            continue

        success = upload_to_senso(filepath)
        if success:
            uploaded += 1
        else:
            failed += 1

        time.sleep(1)

    return uploaded, failed


def main():
    print("=" * 60)
    print("VERITY — Senso Knowledge Base Ingest")
    print("=" * 60)
    print(f"Topics to ingest : {len(SCRAPE_TOPICS)}")
    print(f"Batch size       : {BATCH_SIZE}")
    print(f"Firecrawl limit  : {FIRECRAWL_LIMIT} results/topic")
    print(f"Char limit/file  : {CONTENT_CHAR_LIMIT}")
    print()

    if not FIRECRAWL_API_KEY:
        print("ERROR: FIRECRAWL_API_KEY not set")
        sys.exit(1)

    if not SENSO_API_KEY:
        print("ERROR: SENSO_API_KEY not set")
        sys.exit(1)

    batches = [
        SCRAPE_TOPICS[i:i + BATCH_SIZE]
        for i in range(0, len(SCRAPE_TOPICS), BATCH_SIZE)
    ]
    total_batches = len(batches)
    total_uploaded = 0
    total_failed = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        for batch_num, batch in enumerate(batches, start=1):
            uploaded, failed = process_batch(batch, batch_num, total_batches, output_dir)
            total_uploaded += uploaded
            total_failed += failed

            if batch_num < total_batches:
                print(f"\n  Batch {batch_num} done — pausing 5s before next batch...")
                time.sleep(5)

    print()
    print("=" * 60)
    print(f"Ingest complete: {total_uploaded} uploaded, {total_failed} failed")
    print(f"Total topics processed: {total_uploaded + total_failed}/{len(SCRAPE_TOPICS)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
