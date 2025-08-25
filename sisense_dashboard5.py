# Filename: sisense_dashboard_comparator.py

import streamlit as st
import requests
import json
import re
import pandas as pd

st.set_page_config(layout="wide")
st.title("📊 Multi-Environment Sisense Dashboard Comparator")

# ------------------------- Step 1: Environment Setup -------------------------
num_envs = st.number_input("🌍 How many environments would you like to compare?", 1, 5, 2)

if "env_info" not in st.session_state:
    st.session_state.env_info = {}

st.subheader("🔐 Enter Environment Details")

for i in range(num_envs):
    with st.expander(f"Environment {i + 1}"):
        url = st.text_input(f"Base URL", value="", key=f"url_{i}")
        token = st.text_input(f"API Token", type="password", key=f"token_{i}")
        if st.button(f"🔗 Connect", key=f"connect_{i}"):
            try:
                res = requests.get(f"{url}/api/v1/dashboards", headers={"Authorization": f"Bearer {token}"})
                if res.ok:
                    st.success("✅ Connected")
                    st.session_state.env_info[f"env_{i+1}"] = {"url": url, "token": token}
                else:
                    st.error("❌ Failed to connect. Check URL or token.")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# ------------------------- Step 2: Dashboard Setup -------------------------
if st.session_state.env_info:
    num_dash = st.number_input("📋 Number of dashboards to compare", 2, 10, 2)
    dash_inputs = []

    st.subheader("🆔 Dashboard Inputs")
    for i in range(num_dash):
        col1, col2 = st.columns(2)
        with col1:
            dash_id = st.text_input(f"Dashboard ID {i+1}", key=f"dash_id_{i}")
        with col2:
            env_selected = st.selectbox(f"Select Environment", options=list(st.session_state.env_info.keys()), key=f"env_sel_{i}")
        dash_inputs.append((dash_id, env_selected))

    # ------------------------- Helper Functions -------------------------
    def fetch_dashboard(base_url, dashboard_id, headers):
        try:
            res = requests.get(f"{base_url}/api/v1/dashboards/{dashboard_id}", headers=headers)
            return res.json() if res.ok else None
        except:
            return None

    def get_widgets(base_url, dashboard_id, headers):
        try:
            res = requests.get(f"{base_url}/api/v1/dashboards/{dashboard_id}/widgets", headers=headers)
            return res.json() if res.ok else []
        except:
            return []

    def strip_html_tags(html):
        return re.sub('<[^<]+?>', '', html or '').strip()

    def expand_formula(formula, context):
        for key, val in context.items():
            formula = formula.replace(key, val.get("title", key))
        return formula

    # ------------------------- Replace inside your code -------------------------

    def extract_info(dash):
        filters = [f.get("jaql", {}).get("title", "") for f in dash.get("filters", [])]
        widgets = dash.get("widgets", []) or []
        if isinstance(widgets, dict):
            widgets = widgets.get("widgets", [])

        widget_info, rich_texts, indicators, pivots = [], [], set(), []

        for w in widgets:
            widget_info.append({"title": w.get("title", ""), "type": w.get("type", "")})

            html = w.get("style", {}).get("content", {}).get("html", "")
            if html:
                rich_texts.append(strip_html_tags(html))

            if w.get("type", "").lower() == "indicator":
                for panel in w.get("metadata", {}).get("panels", []):
                    for item in panel.get("items", []):
                        jaql = item.get("jaql", {})
                        title = jaql.get("title", "")
                        context = jaql.get("context", {})
                        for ctx in context.values():
                            panel_name = panel.get("name", "")
                            source = ctx.get("title", "")

                            # Normalize for deduplication
                            dedup_key = (
                                panel_name.strip().lower(),
                                title.strip().lower(),
                                source.strip().lower()
                            )

                            # Store original for display, only if unique key
                            if dedup_key not in indicators:
                                indicators.add(dedup_key)

            if w.get("type", "").lower() == "pivot2":
                for panel in w.get("metadata", {}).get("panels", []):
                    for item in panel.get("items", []):
                        jaql = item.get("jaql", {})
                        if panel.get("name", "").lower() == "values" and "formula" in jaql:
                            formula = expand_formula(jaql["formula"], jaql.get("context", {}))
                            pivots.append((panel.get("name"), jaql.get("title", ""), formula))
                        else:
                            pivots.append((panel.get("name"), jaql.get("title", ""), f"{jaql.get('table', '')}.{jaql.get('column', '')}"))

        # Convert indicators set back to original formatted list
        indicators_list = [
            {"panel": k[0], "title": k[1], "source": k[2]}
            for k in sorted(indicators)
        ]

        return {
            "title": dash.get("title", "Untitled"),
            "filters": filters,
            "widgets": widget_info,
            "rich_text": rich_texts,
            "indicators": [(i["panel"], i["title"], i["source"]) for i in indicators_list],
            "pivots": pivots
        }




    def compare_list(a, b, label, name1, name2):
        union = sorted(set(a + b))
        return pd.DataFrame({
            label: union,
            name1: ["✅" if i in a else "" for i in union],
            name2: ["✅" if i in b else "" for i in union]
        })

    def consolidated_triples(item_key, labels):
        all_rows = {}
        
        def norm(val):
            return val.strip().lower()

        # Step 1: Normalize all rows and store original
        for dash_id, dash in dashboards_info.items():
            raw_items = dash["data"].get(item_key, [])
            normalized_items = set()

            for r in raw_items:
                key = (norm(r[0]), norm(r[1]), norm(r[2]))
                normalized_items.add(key)
                if key not in all_rows:
                    all_rows[key] = {
                        labels[0]: r[0],
                        labels[1]: r[1],
                        labels[2]: r[2],
                        **{dash["title"]: "✅"}
                    }
                else:
                    all_rows[key][dash["title"]] = "✅"

            # Track dashboards where the indicator is not present
            for key in all_rows:
                if dash["title"] not in all_rows[key]:
                    all_rows[key][dash["title"]] = ""

        # Step 2: Build final dataframe
        df = pd.DataFrame(list(all_rows.values()))
        df = df[[*labels, *[dashboards_info[d]["title"] for d in dashboards_info]]]
        return df




    # ------------------------- Comparison -------------------------
    # if st.button("🔍 Compare Dashboards"):
    #     dashboards_info = {}

    #     # Step 1: Load all dashboards
    #     for dash_id, env_key in dash_inputs:
    #         env = st.session_state.env_info[env_key]
    #         headers = {"Authorization": f"Bearer {env['token']}"}
    #         dash = fetch_dashboard(env["url"], dash_id, headers)
    #         widgets = get_widgets(env["url"], dash_id, headers)
    #         if dash:
    #             dash["widgets"] = widgets or []
    #             info = extract_info(dash)
    #             dashboards_info[dash_id] = {
    #                 "title": info["title"],
    #                 "data": info
    #             }

    #         else:
    #             st.error(f"❌ Failed to load dashboard {dash_id}")
    #             st.stop()

    #     dash_ids = list(dashboards_info.keys())
    #     title_map = {dash_id: dashboards_info[dash_id]["title"] for dash_id in dash_ids}
    # ------------------------- Comparison ------------------------- 
    if st.button("🔍 Compare Dashboards"):
        dashboards_info = {}
        for dash_id, env_key in dash_inputs:
            env = st.session_state.env_info[env_key]
            headers = {"Authorization": f"Bearer {env['token']}"}
            dash = fetch_dashboard(env["url"], dash_id, headers)
            widgets = get_widgets(env["url"], dash_id, headers)
            if dash:
                dash["widgets"] = widgets or []
                info = extract_info(dash)
    
                # ✅ Make key unique with env name
                unique_key = f"{env_key}_{dash_id}"
                dashboards_info[unique_key] = {"title": f"{info['title']} ({env_key})", "data": info}
            else:
                st.error(f"❌ Failed to load dashboard {dash_id} from {env_key}")
                st.stop()
    
        dash_ids = list(dashboards_info.keys())
        title_map = {k: dashboards_info[k]["title"] for k in dash_ids}



        # Helper: Consolidated comparison table
        def consolidated_table(item_key, label):
            all_items = set()

            for d in dashboards_info.values():
                items = d["data"].get(item_key, [])
                if items:
                    if isinstance(items[0], dict):
                        items = [i.get("title", "") for i in items]
                    all_items.update(items)

            all_items = sorted(all_items)

            data = {label: all_items}
            for dash_id in dash_ids:
                values = dashboards_info[dash_id]["data"].get(item_key, [])
                if values:
                    if isinstance(values[0], dict):
                        values = [i.get("title", "") for i in values]
                else:
                    values = []
                data[title_map[dash_id]] = ["✅" if item in values else "" for item in all_items]

            return pd.DataFrame(data)



        def consolidated_triples(item_key, labels):
            all_rows = set()

            for d in dashboards_info.values():
                rows = d["data"].get(item_key, [])
                all_rows.update(rows)

            all_rows = sorted(all_rows)

            data = {
                labels[0]: [r[0] for r in all_rows],
                labels[1]: [r[1] for r in all_rows],
                labels[2]: [r[2] for r in all_rows],
            }

            for dash_id in dash_ids:
                values = dashboards_info[dash_id]["data"].get(item_key, [])
                values_set = set(values)
                data[title_map[dash_id]] = ["✅" if r in values_set else "" for r in all_rows]

            return pd.DataFrame(data)




        st.markdown("### 🎯 Filters")
        st.dataframe(consolidated_table("filters", "Filter"), use_container_width=True)

        st.markdown("### 🧩 Widget Titles")
        st.dataframe(consolidated_table("widgets", "Widget Title"), use_container_width=True)

        st.markdown("### ⚙️ Widget Types")
        widget_types = {}

        # Collect widget types for each dashboard
        for k, v in dashboards_info.items():
            widget_types[k] = [w.get("type", "") for w in v["data"].get("widgets", [])]

        # Get unique types
        all_types = sorted(set(sum(widget_types.values(), [])))

        # Build DataFrame
        df_widget_type = pd.DataFrame({
            "Widget Type": all_types,
            **{title_map[k]: ["✅" if t in v else "" for t in all_types] for k, v in widget_types.items()}
        })

        st.dataframe(df_widget_type, use_container_width=True)


        st.markdown("### 📝 Rich Text (Cleaned)")
        st.dataframe(consolidated_table("rich_text", "Rich Text"), use_container_width=True)

        st.markdown("### 📌 Indicators")
        st.dataframe(consolidated_triples("indicators", ["Panel", "Title", "Source"]), use_container_width=True)

        st.markdown("### 🧠 Pivot Columns")
        st.dataframe(consolidated_triples("pivots", ["Panel", "Title", "Formula/Column"]), use_container_width=True)

else:
    st.info("ℹ️ Please connect at least one environment to continue.")

