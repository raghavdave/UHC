import streamlit as st
import altair as alt
import pandas as pd
from pathlib import Path
import seaborn as sns
import matplotlib.pyplot as plt

# === CONFIGURATION ===
RESULT_DIR = Path.cwd() / "results"
COMBINATION_DATA_FILE = "condition_combination_analysis.csv"
DISTRIBUTION_DATA_FILE = "summary_distribution_analysis.csv"

condition_mapping = {
    "SP_ALZHDMTA": "Alzheimer",
    "SP_CHF": "Heart Failure",
    "SP_CHRNKIDN": "Chronic Kidney Disease",
    "SP_CNCR": "Cancer",
    "SP_COPD": "COPD",
    "SP_DEPRESSN": "Depression",
    "SP_DIABETES": "Diabetes",
    "SP_ISCHMCHT": "Ischemic Heart Disease",
    "SP_OSTEOPRS": "Osteoporosis",
    "SP_RA_OA": "RA/OA",
    "SP_STRKETIA": "Stroke",
    # Add all relevant chronic conditions here
}


def map_conditions(condition_str):
    codes = [cond.strip() for cond in condition_str.split(",")]
    readable = [condition_mapping.get(code, code) for code in codes]
    return ", ".join(readable)


# === LOAD DATA ===
@st.cache_data
def load_data():
    combination_df = pd.read_csv(RESULT_DIR / COMBINATION_DATA_FILE)
    combination_df["active_conditions_str"] = combination_df[
        "active_conditions_str"
    ].apply(map_conditions)
    distribution_df = pd.read_csv(RESULT_DIR / DISTRIBUTION_DATA_FILE)
    new_col_names = []
    for i, col_name in enumerate(distribution_df.columns):
        new_col_names.append(
            " ".join(
                [
                    condition_mapping.get(i, i)
                    for i in distribution_df.columns[i].split()
                ]
            )
        )
    distribution_df.columns = new_col_names
    return combination_df, distribution_df


df, df2 = load_data()

tab1, tab2, tab3 = st.tabs(
    ["Univariate Distributions", "Filter Criteria", "Chronic Conditions"]
)

with tab2:
    st.header("Filters for Most Common Chronic Illness Combinations")

    min_conditions = st.slider("Minimum number of chronic conditions", 1, 11, 1)
    min_members = st.slider("Minimum member count", 1, 1000, 1)
    payer_type = st.selectbox(
        "Payer type", ["All", "Medicare", "Beneficiary", "Primary Payer"]
    )
    treatment_type = st.selectbox(
        "Treatment type", ["All", "Inpatient", "Outpatient", "Carrier"]
    )
    submit = st.button("Submit")


# === HELPER FUNCTION TO GET COLUMN NAME ===
def get_cost_column(payer, treatment):
    column_map = {
        "Medicare": {
            "Inpatient": "ip_medicare",
            "Outpatient": "op_medicare",
            "Carrier": "carrier_medicare",
            "All": "total_medicare_cost",
        },
        "Beneficiary": {
            "Inpatient": "ip_beneficiary",
            "Outpatient": "op_beneficiary",
            "Carrier": "carrier_beneficiary",
            "All": "total_beneficiary_cost",
        },
        "Primary Payer": {
            "Inpatient": "ip_pp",
            "Outpatient": "op_pp",
            "Carrier": "carrier_pp",
            "All": "total_pp_cost",
        },
        "All": {
            "Inpatient": "total_ip_cost",
            "Outpatient": "total_op_cost",
            "Carrier": "total_carrier_cost",
            "All": "total_cost",
        },
    }
    return column_map[payer][treatment]


with tab3:
    # === MAIN PAGE ===
    st.title("Chronic Conditions - Summary")

    if submit:
        total_members = df["member_count"].sum()
        filtered_df = df[df["number_of_conditions"] == min_conditions].copy()

        # Compute cost per member and total cost based on selected filter
        cost_col = get_cost_column(payer_type, treatment_type)
        filtered_df["cost_per_member"] = (
            filtered_df[cost_col] / filtered_df["member_count"]
        )
        filtered_df["cost_based_on_filter"] = (
            filtered_df["cost_per_member"] * filtered_df["member_count"]
        )
        filtered_df["perc_population"] = round(
            filtered_df["total_occurrence"] * 100 / total_members, 1
        )

        # === VIEW 1: Most Common Combinations ===
        view_1 = (
            filtered_df[
                ["active_conditions_str", "total_occurrence", "perc_population"]
            ]
            .sort_values(by="total_occurrence", ascending=False)
            .head(5)
            .reset_index(drop=True)
            .rename(
                columns={
                    "active_conditions_str": "Chronic Conditions",
                    "total_occurrence": "Total Occurrence",
                    "perc_population": "% of Total Members",
                }
            )
        )

        st.header("Most Common Chronic Illness Combination")
        try:
            st.write(
                f"[{view_1['Chronic Conditions'][0]}] is the most common combination, "
                f"occurring in **{int(view_1['Total Occurrence'][0])}** members."
            )
            st.dataframe(view_1, hide_index=True)
        except:
            st.warning(f"No combinations found. Change filter criteria.")

        # === VIEW 2: Highest Total Cost ===
        view_2 = (
            filtered_df.loc[
                df["member_count"] >= min_members,
                ["active_conditions_str", "member_count", "cost_based_on_filter"],
            ]
            .sort_values(by="cost_based_on_filter", ascending=False)
            .head(5)
            .reset_index(drop=True)
            .rename(
                columns={
                    "active_conditions_str": "Chronic Conditions",
                    "member_count": "Distinct Member Count",
                    "cost_based_on_filter": "Total Cost ($)",
                }
            )
        )

        st.header("Chronic Illness Combination with Highest Cost")
        try:
            st.write(
                f"Combination [{view_2['Chronic Conditions'][0]}] has the highest total cost "
                f"for **Payer = {payer_type}**, **Treatment = {treatment_type}**, "
                f"costing **${int(view_2['Total Cost ($)'][0])}**."
            )
            st.dataframe(view_2, hide_index=True)
        except:
            st.warning(f"No combinations found. Change filter criteria.")

        # === VIEW 3: Highest Cost Per Member ===
        view_3 = (
            filtered_df.loc[
                df["member_count"] >= min_members,
                ["active_conditions_str", "member_count", "cost_per_member"],
            ]
            .sort_values(by="cost_per_member", ascending=False)
            .head(5)
            .reset_index(drop=True)
            .rename(
                columns={
                    "active_conditions_str": "Chronic Conditions",
                    "member_count": "Distinct Member Count",
                    "cost_per_member": "Cost Per Member ($)",
                }
            )
        )
        view_3["Cost Per Member ($)"] = view_3["Cost Per Member ($)"].astype(int)

        st.header("Chronic Illness Combination with Highest Per Member Cost")
        try:
            st.write(
                f"Combination [{view_3['Chronic Conditions'][0]}] has the highest cost per member "
                f"for **Payer = {payer_type}**, **Treatment = {treatment_type}**, "
                f"costing **${view_3['Cost Per Member ($)'][0]}** per member."
            )
            st.dataframe(view_3, hide_index=True)

            scatter = (
                alt.Chart(view_3)
                .mark_circle(size=100)
                .encode(
                    x=alt.X("Cost Per Member ($)", title="Cost Per Member ($)"),
                    y=alt.Y("Distinct Member Count", title="Distinct Member Count"),
                    tooltip=[
                        "Chronic Conditions",
                        "Cost Per Member ($)",
                        "Distinct Member Count",
                    ],
                )
                .properties(
                    title="Cost Per Member ($) vs Member Count for Top Chronic Condition Combinations",
                    width=400,
                    height=400,
                )
            )

            st.altair_chart(scatter, use_container_width=True)
        except:
            st.warning(f"No combinations found. Change filter criteria.")

    else:
        st.info("Use the Filter Criteria Tab to apply filters and click Submit.")


with tab1:
    # st.title("Univariate Distributions")

    def render_heatmap(
        df: pd.DataFrame, group_col_value: str, title: str, fig_size=(12, 8)
    ):
        """
        Renders a heatmap for a given group column value.
        """
        try:
            # Filter and reshape the data
            summary_df = (
                df.loc[df["Group Column"] == group_col_value]
                .drop(columns=["Group Column"])
                .set_index("Cohort")
                .transpose()
            )

            # Normalize values column-wise
            normalized_df = summary_df.copy()
            for col in normalized_df.columns:
                col_min = normalized_df[col].min()
                col_max = normalized_df[col].max()
                normalized_df[col] = (
                    (normalized_df[col] - col_min) / (col_max - col_min)
                    if col_max > col_min
                    else 0
                )

            # Plot heatmap
            st.header(title)
            fig, ax = plt.subplots(figsize=fig_size)
            sns.heatmap(
                normalized_df,
                annot=summary_df,
                fmt=".1f",
                cmap="YlOrRd",
                linewidths=0.5,
                ax=ax,
            )
            st.pyplot(fig)

        except KeyError:
            st.warning(f"Data not found for {title}")

    # === Render Heatmaps ===
    render_heatmap(df2, "age_bucket", "Age Distribution")
    render_heatmap(df2, "BENE_RACE_CD", "Race Distribution")
    render_heatmap(df2, "SP_STATE_CODE", "State Distribution", fig_size=(40, 16))
    render_heatmap(df2, "BENE_SEX_IDENT_CD", "Sex Distribution")
    render_heatmap(df2, "total_conditions", "Total Chronic Conditions Distribution")
