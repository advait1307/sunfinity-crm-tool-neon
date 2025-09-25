class ResumeManager:
    def __init__(self, run_sql):
        self.run_sql = run_sql

    def load_resumes(self):
        return self.run_sql('SELECT * FROM resumes;')

    def generate_resume_id(self):
        prefix = "RID"
        df = self.run_sql('SELECT "Candidate_ID" FROM resumes ORDER BY "Candidate_ID" DESC LIMIT 1;')
        if df.empty or 'Candidate_ID' not in df.columns:
            return f"{prefix}00001"
        import re
        last_id = str(df.iloc[0]['Candidate_ID'])
        match = re.match(r'RID(\d+)', last_id)
        next_num = int(match.group(1)) + 1 if match else 1
        return f"{prefix}{next_num:05d}"
