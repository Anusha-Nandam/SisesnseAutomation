import streamlit as st
import requests
import json
import re

st.set_page_config(layout="wide")
st.title("📊 Sisense Dashboard Comparator")

# -------------------------------
# Input Section
# -------------------------------
base_url = st.text_input("Sisense Base URL", value="https://qa-pa01.profitsage.net")
api_token = st.text_area("API Token", height=100)
dashboard_id_1 = st.text_input("Dashboard ID 1")
dashboard_id_2 = st.text_input("Dashboard ID 2")

# Optional upload fallback
st.sidebar.header("📁 Upload Dashboard Files (Optional)")
file_1 = st.sidebar.file_uploader("Upload Dashboard 1 (.dash or .json)", type=["json", "dash"])
file_2 = st.sidebar.file_uploader("Upload Dashboard 2 (.dash or .json)", type=["json", "dash"])

# -------------------------------
# Helper Functions
# -------------------------------
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

def get_dashboard_export(base_url, dashboard_id, headers):
    try:
        url = f"{base_url}/api/v1/dashboards/{dashboard_id}/export"
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
        export = get_dashboard_export(base_url, dashboard_id, headers)
        if export:
            return export
    if file:
        return json.load(file)
    return None

def strip_html_tags(html):
    return re.sub('<[^<]+?>', '', html or '').strip()

def extract_dashboard_info(dash):
    filters = [f.get("jaql", {}).get("title", "") for f in dash.get("filters", [])]
    widgets = dash.get("widgets", [])
    if isinstance(widgets, dict):  # for export JSON structure
        widgets = widgets.get("widgets", [])

    titles = [w.get("title", "") for w in widgets]
    types = [w.get("type", "") for w in widgets]

    rich_text_html = []
    rich_text_clean = []

    for w in widgets:
        style = w.get("style", {})
        content = style.get("content", {})
        html = content.get("html", "")
        if html:
            rich_text_html.append(html)
            rich_text_clean.append(strip_html_tags(html))

    return {
        "title": dash.get("title", "Untitled"),
        "filters": filters,
        "widget_titles": titles,
        "widget_types": types,
        "rich_text_html": rich_text_html,
        "rich_text_clean": rich_text_clean
    }


def compare_lists(list1, list2):
    return {
        "only_in_1": sorted(set(list1) - set(list2)),
        "only_in_2": sorted(set(list2) - set(list1)),
        "common": sorted(set(list1) & set(list2))
    }

# -------------------------------
# Comparison Logic
# -------------------------------
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

            st.subheader("📋 Dashboard Titles")
            st.write(f"**Dashboard 1:** {info1['title']}")
            st.write(f"**Dashboard 2:** {info2['title']}")

            st.subheader("📊 Filters Comparison")
            st.json(compare_lists(info1["filters"], info2["filters"]))

            st.subheader("🧩 Widget Titles Comparison")
            st.json(compare_lists(info1["widget_titles"], info2["widget_titles"]))

            st.subheader("⚙️ Widget Types Comparison")
            st.json(compare_lists(info1["widget_types"], info2["widget_types"]))

            st.subheader("📝 Rich Text Content Comparison (`RICHTEXT_MAIN.TITLE`)")
            st.json(compare_lists(info1["rich_text_clean"], info2["rich_text_clean"]))

            st.subheader("📖 Rich Text Content (Plain Text View)")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Dashboard 1 Rich Text")
                for i, text in enumerate(info1["rich_text_clean"], 1):
                    with st.expander(f"Section {i}"):
                        st.write(text)

            with col2:
                st.markdown("### Dashboard 2 Rich Text")
                for i, text in enumerate(info2["rich_text_clean"], 1):
                    with st.expander(f"Section {i}"):
                        st.write(text)

            st.subheader("🧾 Raw HTML (Advanced View)")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Dashboard 1 HTML")
                for i, html in enumerate(info1["rich_text_html"], 1):
                    with st.expander(f"HTML Block {i}"):
                        st.code(html, language="html")

            with col2:
                st.markdown("### Dashboard 2 HTML")
                for i, html in enumerate(info2["rich_text_html"], 1):
                    with st.expander(f"HTML Block {i}"):
                        st.code(html, language="html")

        else:
            st.error("❌ Could not load one or both dashboards.")
