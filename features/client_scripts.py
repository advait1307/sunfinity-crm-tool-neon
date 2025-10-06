import streamlit as st

class ClientUtils:
    def __init__(self, run_sql_func, config):
        self.run_sql = run_sql_func
        self.config = config

    def generate_client_id(self):
        df = self.run_sql('SELECT clients."Client_ID" FROM clients ORDER BY clients."Client_ID" DESC LIMIT 1')
        if df.empty:
            return "CID001"
        last_id = df.iloc[0]['Client_ID']
        num = int(last_id.replace("CID", ""))
        return f"CID{num+1:03d}"

    @staticmethod
    def format_contact(name, number, email):
        return f"{name}|{number}|{email}"

    def make_links(self, files_str):
        if not files_str:
            return "No Files"
        urls = files_str.split('\n')
        links = []
        for url in urls:
            if url:
                df = self.run_sql(f"SELECT filename FROM link_mapping WHERE urllinks = '{url}'")
                display_name = df.iloc[0]['filename'] if not df.empty else "Unknown File"
                links.append(f"[{display_name}]({url})")
        return "<br>".join(links)