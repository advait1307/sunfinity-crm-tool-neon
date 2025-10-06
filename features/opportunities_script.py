import pandas as pd
import streamlit as st
class OpportunitiesManager:
    def __init__(self, run_sql):
        self.run_sql = run_sql

    st.cache()
    def load_opps(self):
        return self.run_sql('SELECT * FROM opportunities;')

    def generate_opp_id(self):
        df = self.run_sql('SELECT "Opportunity_ID" FROM opportunities ORDER BY "Opportunity_ID" DESC LIMIT 1;')
        if df.empty or 'Opportunity_ID' not in df.columns:
            next_num = 1
        else:
            import re
            last_id = df.iloc[0]['Opportunity_ID']
            match = re.match(r'OPP(\d{6})', str(last_id))
            next_num = int(match.group(1)) + 1 if match else 1
        return f"OPP{next_num:06d}"

    st.cache()
    def generate_candidate_links(self, names):
        if not names:
            return ''
        placeholders = ','.join(['%s'] * len(names))
        query = f'SELECT "Name", "Resume" FROM resumes WHERE "Name" IN ({placeholders});'
        df = self.run_sql(query, tuple(names))
        links = []
        for _, row in df.iterrows():
            name = row['Name']
            resume_link = row['Resume']
            if pd.notnull(resume_link) and resume_link not in ['NaN', '', 'No Resume Uploaded']:
                links.append(f"[{name}_resume]({resume_link})")
        return '\n'.join(links)

    def update_candidate_count(self, opp_ids, increment=True):
        for opp_id in opp_ids:
            df = self.run_sql('SELECT "Number of candidates shared" FROM opportunities WHERE "Opp ID" = %s;', (opp_id,))
            if not df.empty:
                current = df.iloc[0]['Number of candidates shared'] or 0
                new_val = max(int(current) + (1 if increment else -1), 0)
                self.run_sql('UPDATE opportunities SET "Number of candidates shared" = %s WHERE "Opp ID" = %s;', (new_val, opp_id))
