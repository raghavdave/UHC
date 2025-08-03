import pandas as pd
import itertools
import logging
from pathlib import Path
from collections import Counter

# === SETUP LOGGING ===
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

# === CONFIGURATION ===
DATA_DIR = Path.cwd() / "data"
RESULT_DIR = Path.cwd() / "results"
RESULT_DIR.mkdir(parents=True, exist_ok=True)

MEMBER_FILENAME = "DE1_0_2009_Beneficiary_Summary_File_Sample_20.csv"
CLAIMS_FILENAME = "DE1_0_2008_to_2010_Outpatient_Claims_Sample_20.csv"
MEMBER_FILE_PATH = DATA_DIR / MEMBER_FILENAME
CLAIMS_FILE_PATH = DATA_DIR / CLAIMS_FILENAME

# === LOAD DATA ===
if not MEMBER_FILE_PATH.exists():
    logging.error(f"File not found: {MEMBER_FILE_PATH}")
    raise FileNotFoundError(f"Data file not found: {MEMBER_FILE_PATH}")

logging.info(f"Loading data from {MEMBER_FILE_PATH}")
df = pd.read_csv(MEMBER_FILE_PATH)
logging.info(f"Loading data from {CLAIMS_FILE_PATH}")
claims_df = pd.read_csv(CLAIMS_FILE_PATH, low_memory=False)

# === IDENTIFY CHRONIC CONDITION COLUMNS ===
chronic_cols = [col for col in df.columns if "SP" in col and col != "SP_STATE_CODE"]
logging.info(f"Chronic condition columns identified: {chronic_cols}")


# === FUNCTIONS ===
def get_active_conditions(row):
    """Returns list of chronic conditions present in a row."""
    return [col for col in chronic_cols if row[col] == 1]


def count_conditions(row):
    """Counts how many chronic conditions are present."""
    return sum(row[col] == 1 for col in chronic_cols)


# === ENRICH DATA ===
df["active_conditions"] = df.apply(get_active_conditions, axis=1)
df["active_conditions_str"] = df["active_conditions"].apply(lambda x: ", ".join(x))
df["total_conditions"] = df.apply(count_conditions, axis=1)

# === DERIVE AGE AND BUCKETS ===
df["age"] = 2008 - (df["BENE_BIRTH_DT"] // 10000)

# Assign age buckets
df["age_bucket"] = pd.cut(
    df["age"],
    bins=[0, 64, 69, 74, 79, 84, 89, float("inf")],
    labels=["25 - 64", "65 - 69", "70 - 74", "75 - 79", "80 - 84", "85 - 89", "90+"],
    right=False,
)

# === COUNT COMBINATIONS ===
logging.info("Generating all chronic condition combinations...")
all_combinations = Counter()

for conditions in df["active_conditions"]:
    for r in range(1, len(conditions) + 1):
        all_combinations.update(itertools.combinations(sorted(conditions), r))

# Convert combination counts to DataFrame
combination_df = pd.DataFrame(
    [
        {
            "number_of_conditions": len(combo),
            "combination": combo,
            "total_occurrence": count,
            "combination_str": ", ".join(combo),
        }
        for combo, count in all_combinations.items()
    ]
)

# === PAYMENT AGGREGATION ===
logging.info("Aggregating payment data by chronic condition set...")

agg_df = (
    df.groupby("active_conditions_str")
    .agg(
        member_count=("DESYNPUF_ID", "count"),
        ip_medicare=("MEDREIMB_IP", "sum"),
        ip_beneficiary=("BENRES_IP", "sum"),
        ip_pp=("PPPYMT_IP", "sum"),
        op_medicare=("MEDREIMB_OP", "sum"),
        op_beneficiary=("BENRES_OP", "sum"),
        op_pp=("PPPYMT_OP", "sum"),
        carrier_medicare=("MEDREIMB_CAR", "sum"),
        carrier_beneficiary=("BENRES_CAR", "sum"),
        carrier_pp=("PPPYMT_CAR", "sum"),
    )
    .reset_index()
)

agg_df["active_conditions_str"].replace("", "NO CHRONIC CONDITIONS", inplace=True)

# === MERGE + COMPUTE COSTS ===
logging.info("Merging combinations with payment data...")

merged_df = agg_df.merge(
    combination_df,
    how="left",
    left_on="active_conditions_str",
    right_on="combination_str",
)

merged_df["chronic_condition_count"] = merged_df["number_of_conditions"].apply(
    lambda x: "<3" if x < 3 else "Multiple"
)

# Cost columns
merged_df["total_ip_cost"] = (
    merged_df["ip_medicare"] + merged_df["ip_beneficiary"] + merged_df["ip_pp"]
)
merged_df["total_op_cost"] = (
    merged_df["op_medicare"] + merged_df["op_beneficiary"] + merged_df["op_pp"]
)
merged_df["total_carrier_cost"] = (
    merged_df["carrier_medicare"]
    + merged_df["carrier_beneficiary"]
    + merged_df["carrier_pp"]
)

merged_df["total_medicare_cost"] = (
    merged_df["ip_medicare"] + merged_df["op_medicare"] + merged_df["carrier_medicare"]
)
merged_df["total_beneficiary_cost"] = (
    merged_df["ip_beneficiary"]
    + merged_df["op_beneficiary"]
    + merged_df["carrier_beneficiary"]
)
merged_df["total_pp_cost"] = (
    merged_df["ip_pp"] + merged_df["op_pp"] + merged_df["carrier_pp"]
)

merged_df["total_cost"] = (
    merged_df["total_ip_cost"]
    + merged_df["total_op_cost"]
    + merged_df["total_carrier_cost"]
)

# Final cleanup
final_df = merged_df.drop(columns=["combination", "combination_str"], errors="ignore")

# === EXPORT RESULT ===
output_path = RESULT_DIR / "condition_combination_analysis.csv"
final_df.to_csv(output_path, index=False)
logging.info(f"Exported final combination analysis to {output_path}")


# === DISTRIBUTION ANALYSIS ===
def summarize_chronic_conditions_by_group(
    df: pd.DataFrame, group_col: str, chronic_cols: list
) -> pd.DataFrame:
    """
    Creates a summary table by demographic group (e.g., Race, Gender, Country),
    showing % of total population and % of each chronic condition population by group.

    Parameters:
    - df: Input DataFrame
    - group_col: Column name to group by (e.g., 'RACE', 'GENDER', 'COUNTRY')
    - chronic_cols: List of chronic condition columns (1 = has condition)

    Returns:
    - A summary DataFrame
    """

    # Normalize chronic condition values to binary 0/1
    df_clean = df.copy()
    for col in chronic_cols:
        df_clean[col] = (df_clean[col] == 1).astype(int)

    total_members = len(df_clean)

    # === Base population distribution by group ===
    base_counts = df_clean[group_col].value_counts().sort_index()
    base_percents = (base_counts / total_members * 100).round(2)

    summary_df = pd.DataFrame(
        {
            "Group Column": group_col,
            "Cohort": base_counts.index,
            "% of Total Population": base_percents.values,
        }
    )

    # === Chronic condition percentages: share of condition population by group ===
    for condition in chronic_cols:
        condition_df = df_clean[df_clean[condition] == 1]

        group_shares = (
            (condition_df[group_col].value_counts(normalize=True) * 100)
            .reindex(summary_df["Cohort"])
            .fillna(0)
            .round(1)
        )

        summary_df[f"% of {condition} Population"] = group_shares.values

    return summary_df


summary_sex = summarize_chronic_conditions_by_group(
    df, "BENE_SEX_IDENT_CD", chronic_cols
)
summary_esrd = summarize_chronic_conditions_by_group(df, "BENE_ESRD_IND", chronic_cols)
summary_state = summarize_chronic_conditions_by_group(df, "SP_STATE_CODE", chronic_cols)
summary_race = summarize_chronic_conditions_by_group(df, "BENE_RACE_CD", chronic_cols)
summary_total_conditions = summarize_chronic_conditions_by_group(
    df, "total_conditions", chronic_cols
)
summary_age = summarize_chronic_conditions_by_group(df, "age_bucket", chronic_cols)

summary_distribution = pd.concat(
    [
        summary_age,
        summary_race,
        summary_esrd,
        summary_state,
        summary_sex,
        summary_total_conditions,
    ],
    axis=0,
    ignore_index=True,
)

summary_distribution.to_csv(
    RESULT_DIR / "summary_distribution_analysis.csv", index=False
)
