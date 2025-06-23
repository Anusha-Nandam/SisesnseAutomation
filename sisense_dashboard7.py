import streamlit as st
import requests
import json
import re
import pandas as pd

st.set_page_config(layout="wide")
st.title("📊 Sisense Dashboard Comparator")

# ------------------------------- Input Section -------------------------------
base_url = st.text_input("Sisense Base URL", value="https://qa-pa01.profitsage.net")
api_token = st.text_area("API Token", height=100)
dashboard_id_1 = st.text_input("Dashboard ID 1")
dashboard_id_2 = st.text_input("Dashboard ID 2")

st.sidebar.header("📁 Upload Dashboard Files (Optional)")
file_1 = st.sidebar.file_uploader("Upload Dashboard 1 (.dash or .json)", type=["json", "dash"])
file_2 = st.sidebar.file_uploader("Upload Dashboard 2 (.dash or .json)", type=["json", "dash"])

# ------------------------------- Helper Functions -------------------------------
def fetch_dashboard(base_url, dashboard_id, headers):
    try:
        url = f"{base_url}/api/v1/dashboards/{dashboard_id}"
        res = requests.get(url, headers=headers)
        if res.ok:
            return res.json()
    except:
        pass
    return None

def get_dashboard_widgets(base_url, dashboard_id, headers):
    try:
        url = f"{base_url}/api/v1/dashboards/{dashboard_id}/widgets"
        res = requests.get(url, headers=headers)
        if res.ok:
            return res.json()
    except:
        pass
    return None

def get_dashboard_data(dashboard_id, file, base_url, headers):
    if dashboard_id:
        dash = fetch_dashboard(base_url, dashboard_id, headers)
        widgets = get_dashboard_widgets(base_url, dashboard_id, headers)
        if dash:
            dash["widgets"] = widgets or []
            return dash
    if file:
        return json.load(file)
    return None

def strip_html_tags(html):
    return re.sub('<[^<]+?>', '', html or '').strip()

def extract_dashboard_info(dash):
    filters = [f.get("jaql", {}).get("title", "") for f in dash.get("filters", [])]
    widgets = dash.get("widgets", [])
    if isinstance(widgets, dict):
        widgets = widgets.get("widgets", [])

    widget_info = []
    rich_text_html = []
    rich_text_clean = []
    indicators = []

    for w in widgets:
        widget_info.append({
            "title": w.get("title", ""),
            "type": w.get("type", "")
        })

        style = w.get("style", {})
        content = style.get("content", {})
        html = content.get("html", "")
        if html:
            rich_text_html.append(html)
            rich_text_clean.append(strip_html_tags(html))

        if w.get("type", "").lower() == "indicator":
            for panel in w.get("metadata", {}).get("panels", []):
                for item in panel.get("items", []):
                    jaql = item.get("jaql", {})
                    title = jaql.get("title", "")
                    context = jaql.get("context", {})
                    for ctx in context.values():
                        indicators.append({
                            "panel": panel.get("name", ""),
                            "title": title,
                            "source": ctx.get("title", "")
                        })

    return {
        "title": dash.get("title", "Untitled"),
        "filters": filters,
        "widgets": widget_info,
        "rich_text_html": rich_text_html,
        "rich_text_clean": rich_text_clean,
        "indicators": indicators
    }

def create_comparison_table(list1, list2, label):
    all_items = sorted(set(list1 + list2))
    df = pd.DataFrame({
        label: all_items,
        "Dashboard 1": ["✅" if item in list1 else "" for item in all_items],
        "Dashboard 2": ["✅" if item in list2 else "" for item in all_items]
    })
    return df

def compare_lists(list1, list2):
    return {
        "only_in_1": sorted(set(list1) - set(list2)),
        "only_in_2": sorted(set(list2) - set(list1)),
        "common": sorted(set(list1) & set(list2))
    }


# ------------------------------- Main Logic -------------------------------
if st.button("🔍 Compare Dashboards"):
    if not (dashboard_id_1 or file_1) or not (dashboard_id_2 or file_2):
        st.warning("Please provide dashboard IDs or upload files for both dashboards.")
    else:
        headers = {"Authorization": f"Bearer {api_token}"} if api_token else {}

        dash1 = get_dashboard_data(dashboard_id_1, file_1, base_url, headers)
        dash2 = get_dashboard_data(dashboard_id_2, file_2, base_url, headers)

        if dash1 and dash2:
            info1 = extract_dashboard_info(dash1)
            info2 = extract_dashboard_info(dash2)

            st.markdown(f"### 🏷️ Dashboard Titles")
            st.write(f"**Dashboard 1:** `{info1['title']}`")
            st.write(f"**Dashboard 2:** `{info2['title']}`")

            st.markdown("---")
            st.markdown("### 🧯 Filters Comparison")
            st.dataframe(create_comparison_table(info1['filters'], info2['filters'], 'Filter'))

            st.markdown("### 📚 Widget Titles Comparison")
            st.dataframe(create_comparison_table(
                [w['title'] for w in info1['widgets']],
                [w['title'] for w in info2['widgets']],
                'Widget Title'))

            st.markdown("### ⚙️ Widget Types Comparison")
            st.dataframe(create_comparison_table(
                [w['type'] for w in info1['widgets']],
                [w['type'] for w in info2['widgets']],
                'Widget Type'))
            
            # ------------------ Rich Text Content Comparison ------------------
            st.markdown("## 📝 Rich Text Content Comparison (<span style='color:#00C853'>RICHTEXT_MAIN.TITLE</span>)", unsafe_allow_html=True)

            rich_cmp_df = create_comparison_table(info1["rich_text_clean"], info2["rich_text_clean"], 'Rich Text')
            st.dataframe(rich_cmp_df, use_container_width=True)

            # ------------------ Rich Text Plain View ------------------
            # st.markdown("## 📄 Cleaned Rich Text (Plain View)")
            # col1, col2 = st.columns(2)

            # with col1:
            #     st.markdown("### Dashboard 1")
            #     for i, text in enumerate(info1["rich_text_clean"], 1):
            #         st.markdown(f"**Section {i}:**")
            #         st.code(text, language="text")

            # with col2:
            #     st.markdown("### Dashboard 2")
            #     for i, text in enumerate(info2["rich_text_clean"], 1):
            #         st.markdown(f"**Section {i}:**")
            #         st.code(text, language="text")

            # # ------------------ Raw HTML View (Optional) ------------------
            # st.markdown("## 🧾 Raw HTML (Optional View)")

            # col1, col2 = st.columns(2)
            # with col1:
            #     st.markdown("### Dashboard 1 HTML Blocks")
            #     for i, html in enumerate(info1['rich_text_html'], 1):
            #         with st.expander(f"HTML Block {i}"):
            #             st.code(html, language="html")

            # with col2:
            #     st.markdown("### Dashboard 2 HTML Blocks")
            #     for i, html in enumerate(info2['rich_text_html'], 1):
            #         with st.expander(f"HTML Block {i}"):
            #             st.code(html, language="html")


            # ------------------ Indicator Comparison ------------------
            st.markdown("## 📌 Indicator Comparison")

            # Prepare comparison lists by converting dicts to string rows
            indicators1 = [f"{i['panel']} | {i['title']} | {i['source']}" for i in info1["indicators"]]
            indicators2 = [f"{i['panel']} | {i['title']} | {i['source']}" for i in info2["indicators"]]

            indicator_cmp_df = create_comparison_table(indicators1, indicators2, "Indicator Detail")
            st.dataframe(indicator_cmp_df, use_container_width=True)

        else:
            st.error("❌ Could not load one or both dashboards.")
