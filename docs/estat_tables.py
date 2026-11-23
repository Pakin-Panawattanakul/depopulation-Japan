"""All 59 prefecture statistics used in the project, for the get_estat() function.

Each entry: short name -> e-Stat table ID, item code, and the web page of the table.
Comment = what it is and which years have data. Generated from config/variables.csv."""

tables = {
    # --- Population, births, deaths, migration ---
    "population": {"table_id": "0000010101", "item_code": "A1101", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Total population, 1975-2024
    "births": {"table_id": "0000010101", "item_code": "A4101", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Births, 1980-2023
    "deaths": {"table_id": "0000010101", "item_code": "A4200", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Deaths, 1975-2023
    "moves_in": {"table_id": "0000010101", "item_code": "A5101", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Moves in (Japanese nationals), 1975-2025
    "moves_out": {"table_id": "0000010101", "item_code": "A5102", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Moves out (Japanese nationals), 1975-2025
    # --- Age and family ---
    "pop_65plus": {"table_id": "0000010101", "item_code": "A1303", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Population aged 65+, 1975-2024
    "female_20_24": {"table_id": "0000010101", "item_code": "A120502", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Women aged 20-24, 1975-2024
    "female_25_29": {"table_id": "0000010101", "item_code": "A120602", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Women aged 25-29, 1975-2024
    "female_30_34": {"table_id": "0000010101", "item_code": "A120702", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Women aged 30-34, 1975-2024
    "female_35_39": {"table_id": "0000010101", "item_code": "A120802", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Women aged 35-39, 1975-2024
    "tfr": {"table_id": "0000010201", "item_code": "#A05203", "link": "https://www.e-stat.go.jp/dbview?sid=0000010201"},  # Total fertility rate, 1980-2023
    "unmarried_f_30_34": {"table_id": "0000010101", "item_code": "A1601042", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Unmarried women aged 30-34, 1980-2020
    # --- Economy and jobs ---
    "taxable_income": {"table_id": "0000010103", "item_code": "C120110", "link": "https://www.e-stat.go.jp/dbview?sid=0000010103"},  # Taxable income (thousand yen), 1985-2024
    "taxpayers": {"table_id": "0000010103", "item_code": "C120120", "link": "https://www.e-stat.go.jp/dbview?sid=0000010103"},  # Number of taxpayers (income levy), 1985-2024
    "unemployment_rate": {"table_id": "0000010206", "item_code": "#F01301", "link": "https://www.e-stat.go.jp/dbview?sid=0000010206"},  # Unemployment rate (%), 1975-2020
    "job_openings_ratio": {"table_id": "0000010206", "item_code": "#F03103", "link": "https://www.e-stat.go.jp/dbview?sid=0000010206"},  # Active job openings-to-applicants ratio, 1975-2022
    # --- City / countryside ---
    "did_population": {"table_id": "0000010101", "item_code": "A1801", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Population in densely inhabited districts, 1975-2020
    # --- Housing ---
    "vacancy_rate": {"table_id": "0000010208", "item_code": "#H01405", "link": "https://www.e-stat.go.jp/dbview?sid=0000010208"},  # Vacant dwelling ratio (%), 1978-2023
    "land_price_res": {"table_id": "0000010103", "item_code": "C5401", "link": "https://www.e-stat.go.jp/dbview?sid=0000010103"},  # Residential land standard price (yen/m2), 1976-2024
    # --- Education ---
    "univ_entrants_other_pref": {"table_id": "0000010105", "item_code": "E470202", "link": "https://www.e-stat.go.jp/dbview?sid=0000010105"},  # University entrants from this prefecture's high schools going to another prefecture, 2000-2024
    "univ_entrants_total": {"table_id": "0000010105", "item_code": "E470205", "link": "https://www.e-stat.go.jp/dbview?sid=0000010105"},  # University entrants from this prefecture's high schools, 1980-2024
    "univ_capacity_index": {"table_id": "0000010205", "item_code": "#E0610202", "link": "https://www.e-stat.go.jp/dbview?sid=0000010205"},  # University capacity index, 1976-2024
    "hs_grads_jobs_other_pref": {"table_id": "0000010206", "item_code": "#F03302", "link": "https://www.e-stat.go.jp/dbview?sid=0000010206"},  # Share of high-school graduates taking a job in another prefecture, 1975-2023
    "local_univ_entry_share": {"table_id": "0000010205", "item_code": "#E0940302", "link": "https://www.e-stat.go.jp/dbview?sid=0000010205"},  # Share of university entrants from local high schools entering a local university, 1980-2024
    # --- Health ---
    "doctors": {"table_id": "0000010109", "item_code": "I6100", "link": "https://www.e-stat.go.jp/dbview?sid=0000010109"},  # Number of doctors, 1975-2022
    # --- Public finance ---
    "fiscal_strength": {"table_id": "0000010104", "item_code": "D2101", "link": "https://www.e-stat.go.jp/dbview?sid=0000010104"},  # Fiscal strength index (prefectural finance), 1975-2022
    # --- Weather ---
    "snow_days": {"table_id": "0000010102", "item_code": "B4107", "link": "https://www.e-stat.go.jp/dbview?sid=0000010102"},  # Days of snowfall per year, 1975-2020
    # --- Marriage, wages, housing, childcare (birth-rate step) ---
    "married_f_20_24": {"table_id": "0000010101", "item_code": "A1602022", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Married women aged 20-24 (census), 1975-2020
    "married_f_25_29": {"table_id": "0000010101", "item_code": "A1602032", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Married women aged 25-29 (census), 1975-2020
    "married_f_30_34": {"table_id": "0000010101", "item_code": "A1602042", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Married women aged 30-34 (census), 1975-2020
    "married_f_35_39": {"table_id": "0000010101", "item_code": "A1602052", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Married women aged 35-39 (census), 1975-2020
    "married_f_40_44": {"table_id": "0000010101", "item_code": "A1602062", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Married women aged 40-44 (census), 1980-2020
    "female_40_44": {"table_id": "0000010101", "item_code": "A120902", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Women aged 40-44, 1975-2024
    "marriage_rate": {"table_id": "0000010201", "item_code": "#A06601", "link": "https://www.e-stat.go.jp/dbview?sid=0000010201"},  # Marriages per 1000 population, 1975-2022
    "homeownership_rate": {"table_id": "0000010208", "item_code": "#H01301", "link": "https://www.e-stat.go.jp/dbview?sid=0000010208"},  # Owner-occupied housing share (%), 1978-2023
    "floor_area_owned": {"table_id": "0000010208", "item_code": "#H0210301", "link": "https://www.e-stat.go.jp/dbview?sid=0000010208"},  # Floor area per owner-occupied dwelling (m2), 1978-2023
    "floor_area_rented": {"table_id": "0000010208", "item_code": "#H0210302", "link": "https://www.e-stat.go.jp/dbview?sid=0000010208"},  # Floor area per rented dwelling (m2), 1978-2023
    "rent_private": {"table_id": "0000010208", "item_code": "#H04102", "link": "https://www.e-stat.go.jp/dbview?sid=0000010208"},  # Private rent per 3.3 m2 per month (yen), 1975-2024
    "long_commute_share": {"table_id": "0000010208", "item_code": "#H03101", "link": "https://www.e-stat.go.jp/dbview?sid=0000010208"},  # Employee households with 90+ min commute (per 1000), 1978-2018
    "nurseries_per_child": {"table_id": "0000010205", "item_code": "#E0110105", "link": "https://www.e-stat.go.jp/dbview?sid=0000010205"},  # Nurseries per 100k children aged 0-5, 1975-2020
    "childcare_use_rate": {"table_id": "0000010205", "item_code": "#E0910402", "link": "https://www.e-stat.go.jp/dbview?sid=0000010205"},  # Childcare (nursery) usage rate (%), 1975-2020
    "waitlisted_children": {"table_id": "0000010110", "item_code": "J250502", "link": "https://www.e-stat.go.jp/dbview?sid=0000010110"},  # Children on nursery waiting lists, 2001-2024
    "dual_income_share": {"table_id": "0000010206", "item_code": "#F01503", "link": "https://www.e-stat.go.jp/dbview?sid=0000010206"},  # Dual-income household share (%), 1980-2020
    "labor_force_f": {"table_id": "0000010106", "item_code": "F110102", "link": "https://www.e-stat.go.jp/dbview?sid=0000010106"},  # Female labor force, 1975-2020
    "not_in_labor_force_f": {"table_id": "0000010106", "item_code": "F110802", "link": "https://www.e-stat.go.jp/dbview?sid=0000010106"},  # Female population not in labor force, 1975-2020
    "unemployment_rate_f": {"table_id": "0000010206", "item_code": "#F0130102", "link": "https://www.e-stat.go.jp/dbview?sid=0000010206"},  # Female unemployment rate (%), 1975-2020
    "nuclear_family_share": {"table_id": "0000010201", "item_code": "#A06202", "link": "https://www.e-stat.go.jp/dbview?sid=0000010201"},  # Nuclear-family household share (%), 1980-2020
    "univ_rate_f": {"table_id": "0000010105", "item_code": "E470102", "link": "https://www.e-stat.go.jp/dbview?sid=0000010105"},  # University/college advancement rate of female high-school graduates, 2000-2023
    "wage_m": {"table_id": "0000010106", "item_code": "F620201", "link": "https://www.e-stat.go.jp/dbview?sid=0000010106"},  # Monthly scheduled wage men (thousand yen; up to 2019), 1975-2019
    "wage_m_2020": {"table_id": "0000010106", "item_code": "F620217", "link": "https://www.e-stat.go.jp/dbview?sid=0000010106"},  # Monthly scheduled wage men (thousand yen; 2020 onward), 2020-2024
    "wage_f": {"table_id": "0000010106", "item_code": "F620202", "link": "https://www.e-stat.go.jp/dbview?sid=0000010106"},  # Monthly scheduled wage women (thousand yen; up to 2019), 1975-2019
    "wage_f_2020": {"table_id": "0000010106", "item_code": "F620218", "link": "https://www.e-stat.go.jp/dbview?sid=0000010106"},  # Monthly scheduled wage women (thousand yen; 2020 onward), 2020-2024
    "births_m20_24": {"table_id": "0000010101", "item_code": "A410203", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Births to mothers aged 20-24, 1975-2007
    "births_m25_29": {"table_id": "0000010101", "item_code": "A410204", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Births to mothers aged 25-29 (1975-2007), 1975-2007
    "births_m30_34": {"table_id": "0000010101", "item_code": "A410205", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Births to mothers aged 30-34 (1975-2007), 1975-2007
    "births_m35_39": {"table_id": "0000010101", "item_code": "A410206", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Births to mothers aged 35-39 (1975-2007), 1975-2007
    "births_m40_44": {"table_id": "0000010101", "item_code": "A410207", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Births to mothers aged 40-44 (1975-2007), 1975-2007
    "dual_income_households": {"table_id": "0000010106", "item_code": "F1501", "link": "https://www.e-stat.go.jp/dbview?sid=0000010106"},  # Dual-income households (count), 1980-2020
    "married_f_15plus": {"table_id": "0000010101", "item_code": "A1602002", "link": "https://www.e-stat.go.jp/dbview?sid=0000010101"},  # Married women aged 15+ (one per married couple), 1975-2020
}
