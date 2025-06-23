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

def create_comparison_table(list1, list2, label, name1="Dashboard 1", name2="Dashboard 2"):
    all_items = sorted(set(list1 + list2))
    df = pd.DataFrame({
        label: all_items,
        name1: ["✅" if item in list1 else "" for item in all_items],
        name2: ["✅" if item in list2 else "" for item in all_items]
    })
    return df

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

            title1 = info1["title"]
            title2 = info2["title"]

            st.markdown(f"### 🏷️ Dashboard Titles")
            st.write(f"**{title1}** (from `{dashboard_id_1}`)")
            st.write(f"**{title2}** (from `{dashboard_id_2}`)")

            st.markdown("---")
            st.markdown("### 🧯 Filters Comparison")
            st.dataframe(create_comparison_table(info1['filters'], info2['filters'], 'Filter', title1, title2))

            st.markdown("### 📚 Widget Titles Comparison")
            st.dataframe(create_comparison_table(
                [w['title'] for w in info1['widgets']],
                [w['title'] for w in info2['widgets']],
                'Widget Title', title1, title2))

            st.markdown("### ⚙️ Widget Types Comparison")
            st.dataframe(create_comparison_table(
                [w['type'] for w in info1['widgets']],
                [w['type'] for w in info2['widgets']],
                'Widget Type', title1, title2))

            st.markdown("## 📝 Rich Text Comparison (<span style='color:#00C853'>RICHTEXT_MAIN.TITLE</span>)", unsafe_allow_html=True)
            st.dataframe(create_comparison_table(
                info1["rich_text_clean"],
                info2["rich_text_clean"],
                "Rich Text", title1, title2
            ), use_container_width=True)

            st.markdown("## 📌 Indicator Comparison")
            ind1 = [f"{i['panel']} | {i['title']} | {i['source']}" for i in info1["indicators"]]
            ind2 = [f"{i['panel']} | {i['title']} | {i['source']}" for i in info2["indicators"]]
            st.dataframe(create_comparison_table(
                ind1, ind2, "Indicator Detail", title1, title2
            ), use_container_width=True)
        else:
            st.error("❌ Could not load one or both dashboards.")
