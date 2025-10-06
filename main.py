import streamlit as st
import pandas as pd
import yaml
import psycopg2
import re
import io
from datetime import date
from features.client_scripts import ClientUtils
from features.client_files_uploader import ClientOneDriveUploader
from features.opportunities_script import OpportunitiesManager
from features.job_description_uploader import OneDriveJDUploader
from features.resume_uploader import OneDriveUploader
from features.resumes_script import ResumeManager

st.set_page_config(page_title = 'Sunfinty-CRM', layout="wide")
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

db_conf = config['database']
conn = psycopg2.connect(
    host=db_conf['host'],
    dbname=db_conf['dbname'],
    user=db_conf['user'],
    password=db_conf['password'],
    port=db_conf['port'],
    sslmode=db_conf['sslmode']
)

def run_sql(query, params=None):
    if query.strip().lower().startswith("select"):
        df = pd.read_sql(query, conn, params=params)
        return df
    else:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
        return 1


client_uploader_obj = ClientOneDriveUploader(run_sql, config)
client_function_obj = ClientUtils(run_sql, config)
opportunities_obj = OpportunitiesManager(run_sql)
jd_uploader_obj = OneDriveJDUploader(config)
resumes_obj = ResumeManager(run_sql)
file_upload_obj = OneDriveUploader(config)


pages = st.sidebar.radio('Select Page', ['Clients', 'Opportunities', 'Candidate Manager'])
if pages == 'Clients':
    st.title('Client Manager')
    tab1, tab2, tab3 = st.tabs(['View Clients', 'Insert New Client', 'Update Client'])
    with tab1:
        df = run_sql('SELECT * FROM clients order by "Client_ID" asc;')
        if df.empty:
            st.info("No data is present for clients.")
        else:
            search_query = st.text_input('Search')
            if search_query:
                pattern = re.escape(search_query)
                search_cols = ['Client_Name', 'Location', 'Contact_Person_1', 'Contact_Person_2', 'Contact_Person_3']
                mask = df[search_cols].apply(lambda x: x.astype(str).str.contains(pattern, case=False, na=False)).any(axis=1)
                filtered_df = df.loc[mask].copy()
            else:
                filtered_df = df.copy()

            filtered_df['Agreements'] = filtered_df['Agreements'].apply(client_function_obj.make_links)
            for col in ['Contact_Person_1', 'Contact_Person_2', 'Contact_Person_3']:
                filtered_df[col] = filtered_df[col].str.replace('|', '\\|', regex=False)
            excel_buffer = io.BytesIO()
            filtered_df.to_excel(excel_buffer, index=False)
            st.download_button(
                label="⬇️ Download as Excel",
                data=excel_buffer.getvalue(),
                file_name="clients.xlsx",
                key="download_clients_excel",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.markdown(filtered_df.to_markdown(index=False), unsafe_allow_html=True)
    with tab2:
        with st.form('new_client'):
            client_id = client_function_obj.generate_client_id()
            client_name = st.text_input('Client Name')
            st.text(f"Client ID: {client_id}")
            location = st.text_input('Location')
            contact1 = client_function_obj.format_contact(
                st.text_input('Contact Person 1 Name'),
                st.text_input('Contact Person 1 Number'),
                st.text_input('Contact Person 1 Email')
            )
            contact2 = client_function_obj.format_contact(
                st.text_input('Contact Person 2 Name'),
                st.text_input('Contact Person 2 Number'),
                st.text_input('Contact Person 2 Email')
            )
            contact3 = client_function_obj.format_contact(
                st.text_input('Contact Person 3 Name'),
                st.text_input('Contact Person 3 Number'),
                st.text_input('Contact Person 3 Email')
            )
            onboarding = st.selectbox('Onboarding status', ['Completed', 'in-process', 'Rejected'])
            agreement_files = st.file_uploader('Upload Agreement Files', accept_multiple_files=True)
            project = st.text_input('Project Name (if any)')
            submitted = st.form_submit_button('Submit')

            if submitted:
                file_urls = []
                if agreement_files:
                    for file in agreement_files:
                        url = client_uploader_obj.outlook_file_uploader(client_name, file)
                        file_urls.append(url)
                files_str = "\n".join(file_urls)
                query = f'INSERT INTO clients ("Client_ID", "Client_Name", "Location", "Contact_Person_1", "Contact_Person_2", "Contact_Person_3", "Onboarding_status", "Agreements", "Project") VALUES (\'{client_id}\', \'{client_name}\', \'{location}\', \'{contact1}\', \'{contact2}\', \'{contact3}\', \'{onboarding}\', \'{files_str}\', \'{project}\');'
                run_sql(query)
                st.success("Client added!")
                st.rerun()
    with tab3:
        df = run_sql("SELECT * FROM clients;")
        if df.empty:
            st.info("No data is present for clients.")
        else:
            client_names = df['Client_Name'].tolist()
            selected_client = st.selectbox('Select Client to Update', client_names)
            client_row = df[df['Client_Name'] == selected_client].iloc[0]
            client_name = st.text_input('Client Name', value=client_row['Client_Name'], disabled=True)
            location = st.text_input('Location', value=client_row['Location'])
            contact1 = st.text_input('Contact Person 1', value=client_row['Contact_Person_1'])
            contact2 = st.text_input('Contact Person 2', value=client_row['Contact_Person_2'])
            contact3 = st.text_input('Contact Person 3', value=client_row['Contact_Person_3'])
            onboarding = st.selectbox('Onboarding status', ['Completed', 'in-process', 'Rejected'],
                                      index=['Completed', 'in-process', 'Rejected'].index(client_row['Onboarding_status']))
            project = st.text_input('Project Name (if any)', value=client_row['Project'])
            st.markdown("**Existing Agreement Links:**")
            existing_links = client_row['Agreements'].split('\n') if client_row['Agreements'] else []
            links_to_keep = []
            for i, link in enumerate(existing_links):
                col1, col2 = st.columns([8, 1])
                with col1:
                    st.markdown(f"[Link {i + 1}]({link})")
                with col2:
                    if not st.checkbox(f"Delete Link {i + 1}", key=f"del_{i}"):
                        links_to_keep.append(link)
            st.markdown("**Add New Agreement Files:**")
            new_files = st.file_uploader('Upload New Agreement Files', accept_multiple_files=True, key='update_files')
            new_file_urls = []
            if new_files:
                for file in new_files:
                    url = client_uploader_obj.outlook_file_uploader(client_name, file)
                    new_file_urls.append(url)
            updated_links = links_to_keep + new_file_urls
            updated_links_str = "\n".join(updated_links)

            if st.button('Update Client'):
                query = f'''
                    UPDATE clients SET
                        "Client_Name" = %s,
                        "Location" = %s,
                        "Contact_Person_1" = %s,
                        "Contact_Person_2" = %s,
                        "Contact_Person_3" = %s,
                        "Onboarding_status" = %s,
                        "Agreements" = %s,
                        "Project" = %s
                    WHERE "Client_ID" = %s;
                    '''
                run_sql(query, (
                    client_name, location, contact1, contact2, contact3, onboarding, updated_links_str, project,
                    client_row['Client_ID']
                ))
                st.success("Client updated successfully!")
                st.rerun()
            if st.button('Delete Client'):
                query = 'DELETE FROM clients WHERE "Client_ID" = %s;'
                run_sql(query, (client_row['Client_ID'],))
                st.warning("Client deleted!")
                st.rerun()

elif pages == 'Opportunities':
    st.title('Opportunities Manager')
    df_clients = run_sql('SELECT * FROM clients;')
    client_list = df_clients['Client_Name'].tolist() if not df_clients.empty else []
    df_opps = run_sql('SELECT * FROM opportunities order by "Opportunity_ID";')
    df_resumes = run_sql('SELECT * FROM resumes;')
    resume_choices = df_resumes['Name'].tolist() if not df_resumes.empty and 'Name' in df_resumes.columns else []
    tab1, tab2, tab3 = st.tabs(['View Opportunities', 'Insert New Opportunity', 'Update Opportunity'])

    with tab1:
        if df_opps.empty:
            st.info('No opportunities available.')
        else:
            col1, col2 = st.columns([8, 1])
            with col1:
                search_term = st.text_input('Search opportunities')
            with col2:
                deal_status_options = ['All'] + df_opps['Deal_Status'].dropna().unique().tolist()
                selected_status = st.selectbox('Deal Status', deal_status_options)

            df_display = df_opps.copy()
            if selected_status != 'All':
                df_display = df_display[df_display['Deal_Status'] == selected_status]

            if search_term:
                pattern = re.escape(search_term)
                mask = df_display.astype(str).agg(' '.join, axis=1).str.contains(pattern, case=False, na=False)
                df_display = df_display[mask]
            if 'JD' in df_display.columns:
                df_display['JD'] = df_display.apply(
                    lambda row: f"[View JD]({row['JD']})" if pd.notnull(row['JD']) and row['JD'] not in ['NaN', '','No Job Description Uploaded'] else row['JD'],axis=1)
            if 'Name_of_Candidates_Shortlisted' in df_display.columns:
                df_display['Name_of_Candidates_Shortlisted'] = df_display['Name_of_Candidates_Shortlisted'].apply(lambda x: x.replace('\n', '<br>') if isinstance(x, str) else x)
            excel_buffer = io.BytesIO()
            df_display.to_excel(excel_buffer, index=False)
            st.download_button(
                label="⬇️ Download as Excel",
                data=excel_buffer.getvalue(),
                file_name="opportunities.xlsx",
                key="download_opportunities_excel",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.markdown(df_display.to_markdown(index=False), unsafe_allow_html=True)
    with tab2:
        if not client_list:
            st.info('No clients available. Please add clients first.')
        else:
            with st.form('new_opportunity'):
                # You may want to implement your own generate_opp_id using SQL
                opp_id = opportunities_obj.generate_opp_id()
                client_name = st.selectbox('Client name', client_list)
                st.text(f"opportunity_id: {opp_id}")
                role = st.text_input('Role')
                date_received = st.date_input('Date received', value=date.today())
                job_location = st.text_input('Job Location')
                exp_bracket = st.text_input('Experience bracket')
                budget = st.text_input('Budget')
                expected_notice = st.text_input('Expected notice period')
                priority = st.selectbox('Priority', ['High', 'Medium', 'Low'])
                special_comments = st.text_area('Special comments')
                deal_status = st.selectbox('Deal Status', ['Open', 'Closed', 'Hold', 'Won'])
                jd_file = st.file_uploader('JD (upload file)')
                candidate_names = st.multiselect('Name of candidates shared', resume_choices)
                closed_on = None
                submitted = st.form_submit_button('Submit')
                if submitted:
                    jd_one_drive_path = jd_uploader_obj.outlook_jd_uploader(client_name, role, str(date_received), opp_id, jd_file) if jd_file else 'No Job Description Uploaded'
                    candidates_markdown = opportunities_obj.generate_candidate_links(candidate_names)
                    query = '''
                        INSERT INTO opportunities (
                            "Client_Name", "Role", "Opportunity_ID", "Date_Received", "JD", "Job_Location", "Experience_Bracket",
                            "Budget", "Expected_Notice_Period", "Priority", "Special_Comments", "Deal_Status",
                            "Number_of_Candidates_Shared", "Name_of_Candidates_Shortlisted", "Closed_On"
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    '''
                    run_sql(query, (
                        client_name, role, opp_id, date_received, jd_one_drive_path, job_location, exp_bracket,
                        budget, expected_notice, priority, special_comments, deal_status,
                        len(candidate_names), candidates_markdown, closed_on
                    ))
                    st.success(f'Opportunity {opp_id} added!')
                    st.rerun()
    with tab3:
        if df_opps.empty:
            st.info('No opportunities available to update.')
        else:
            dropdown_labels = [
                f"{row['Opportunity_ID']} - {row['Client_Name']} - {row['Role']}"
                for _, row in df_opps.iterrows()
            ]
            dropdown_values = df_opps['Opportunity_ID'].tolist()
            label_to_id = dict(zip(dropdown_labels, dropdown_values))

            selected_label = st.selectbox('Select opportunity to update', dropdown_labels)
            selected = label_to_id[selected_label]
            opp_row = df_opps[df_opps['Opportunity_ID'] == selected].iloc[0]
            with st.form('update_opportunity'):
                client_name = st.selectbox('Client name', client_list, index=client_list.index(opp_row['Client_Name']), disabled=True)
                role = st.text_input('Role', opp_row['Role'], disabled=True)
                date_received = st.date_input('Date Received', opp_row['Date_Received'])
                job_location = st.text_input('Job Location', opp_row['Job_Location'])
                exp_bracket = st.text_input('Experience Bracket', opp_row['Experience_Bracket'])
                budget = st.text_input('Budget', opp_row['Budget'])
                expected_notice = st.text_input('Expected Notice Period', opp_row['Expected_Notice_Period'])
                priority = st.selectbox('Priority', ['High', 'Medium', 'Low'], index=['High', 'Medium', 'Low'].index(opp_row['Priority']))
                special_comments = st.text_area('Special Comments', opp_row['Special_Comments'])
                deal_status = st.selectbox('Deal Status', ['Open', 'Closed', 'Hold', 'Won'], index=['Open', 'Closed', 'Hold', 'Won'].index(opp_row['Deal_Status']))
                st.text_input('Number of Candidates Shared', value=str(int(opp_row['Number_of_Candidates_Shared'])), disabled=True)
                current_candidates = re.findall(r'\[([^\]_]+)_resume\]', opp_row['Name_of_Candidates_Shortlisted']) if pd.notnull(opp_row['Name_of_Candidates_Shortlisted']) else []
                candidate_names = st.multiselect('Name of Candidates Shared', resume_choices, current_candidates)
                is_closed = st.radio("Is the opportunity closed?", ['Yes', 'No'], index=0 if opp_row['Deal_Status'] == 'Closed' else 1)
                closed_on = st.date_input('Closed On',opp_row['Closed_On'] if pd.notnull(opp_row['Closed_On']) else date.today())
                if is_closed == 'No':
                    closed_on = None
                jd_file = st.file_uploader('Upload JD to update the existing one')
                submitted = st.form_submit_button('Update')
                delete_clicked = st.form_submit_button('Delete')
                if submitted:
                    candidates_markdown = opportunities_obj.generate_candidate_links(candidate_names)
                    jd_one_drive_path = jd_uploader_obj.outlook_jd_uploader(client_name, role, str(date_received), selected, jd_file) if jd_file else opp_row['JD']
                    query = '''
                        UPDATE opportunities SET
                            "Client_Name" = %s,
                            "Role" = %s,
                            "Date_Received" = %s,
                            "Job_Location" = %s,
                            "Experience_Bracket" = %s,
                            "Budget" = %s,
                            "Expected_Notice_Period" = %s,
                            "Priority" = %s,
                            "Special_Comments" = %s,
                            "Deal_Status" = %s,
                            "Closed_On" = %s,
                            "JD" = %s,
                            "Name_of_Candidates_Shortlisted" = %s,
                            "Number_of_Candidates_Shared" = %s
                        WHERE "Opportunity_ID" = %s;
                    '''
                    run_sql(query, (
                        client_name, role, date_received, job_location, exp_bracket, budget, expected_notice,
                        priority, special_comments, deal_status, closed_on, jd_one_drive_path,
                        candidates_markdown, len(candidate_names), selected
                    ))
                    st.success(f'Opportunity {selected} updated!')
                    st.rerun()
                if delete_clicked:
                    query = 'DELETE FROM opportunities WHERE "Opportunity_ID" = %s;'
                    run_sql(query, (selected,))
                    st.warning(f'Opportunity {selected} deleted!')
                    st.rerun()

elif pages == 'Candidate Manager':
    st.title('Candidate Manager')
    tab1, tab2, tab3 = st.tabs(['View Candidates', 'Insert New Candidate', 'Update Candidate'])
    df_resumes = run_sql('SELECT * FROM resumes;')
    df_opps = run_sql('SELECT * FROM opportunities;')
    opp_choices = [
        f"{row['Role']} ({row['Client_Name']}:{row['Opportunity_ID']})"
        for _, row in df_opps[df_opps['Deal_Status'] != 'Closed'].iterrows()
    ] if not df_opps.empty else []

    with tab1:
        if df_resumes.empty:
            st.info('No resumes available.')
        else:
            search_term = st.text_input('Search resumes')
            df_display = df_resumes.copy()
            if search_term:
                import re
                pattern = re.escape(search_term)
                mask = df_display.astype(str).agg(' '.join, axis=1).str.contains(pattern, case=False, na=False)
                df_display = df_display[mask]
            def parse_roles(roles_str):
                if not roles_str or roles_str == 'No Role':
                    return roles_str
                roles = []
                for role_val in roles_str.split(';'):
                    match = re.match(r'(.+?) \((.+?):(.+?)\)', role_val)
                    if match:
                        role_name, company, job_id = match.groups()
                        roles.append(f"{role_name} ({company}, {job_id})")
                    else:
                        roles.append(role_val)
                return ', '.join(roles)
            df_display['Identified_for_Roles'] = df_display['Identified_for_Roles'].str.replace(':', '\\-')
            df_display['Identified_for_Roles'] = df_display['Identified_for_Roles'].str.replace(';', '<br>')
            if 'Identified for roles' in df_display.columns:
                df_display['Identified for roles'] = df_display['Identified for roles'].apply(parse_roles)
            if 'Resume' in df_display.columns:
                df_display['Resume'] = df_display.apply(
                    lambda row: (
                        f"[{row['Name']}_resume]({row['Resume']})"
                        if pd.notnull(row['Resume'])
                           and row['Resume'] not in ['NaN', '', 'No Resume Uploaded']
                        else row['Resume']
                    ),
                    axis=1
                )
            excel_buffer = io.BytesIO()
            df_display.to_excel(excel_buffer, index=False)
            st.download_button(
                label="⬇️ Download as Excel",
                data=excel_buffer.getvalue(),
                file_name="candidates.xlsx",
                key="download_candidates_excel",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.markdown(df_display.to_markdown(index=False), unsafe_allow_html=True)
    with tab2:
        with st.form('new_resume'):
            # You may want to implement your own generate_resume_id using SQL
            entry_id = resumes_obj.generate_resume_id()
            st.text(f"Candidate_ID: {entry_id}")
            name = st.text_input('Name')
            source = st.text_input('Source')
            top_skills = st.text_input('Top Skills')
            location = st.text_input('Location')
            current_org = st.text_input('Current organization')
            screener_name = st.text_input('Screener Name')
            screener_comments = st.text_area('Screener comments')
            first_interviewer = st.text_input('First Interviewer name')
            first_interviewer_comments = st.text_area('First interviewer comments')
            identified_roles = st.multiselect('Identified for roles', opp_choices)
            years_exp = st.text_input('Years of experience')
            current_ctc = st.text_input('Current CTC')
            resume_file = st.file_uploader('Resume (upload file)')
            submitted = st.form_submit_button('Submit')
            if submitted:
                resume_uploaded_path = file_upload_obj.outlook_file_uploader(name, resume_file) if resume_file else 'No Resume Uploaded'
                if not identified_roles:
                    identified_roles_str = 'No Role'
                else:
                    identified_roles_str = ';'.join(identified_roles)
                for opp in identified_roles:
                    opp_id = opp.split(':')[-1].rstrip(')')
                    run_sql('UPDATE opportunities SET "Number_of_Candidates_Shared" = "Number_of_Candidates_Shared" + 1 WHERE "Opportunity_ID" = %s;',(opp_id,))

                query = '''
                    INSERT INTO resumes (
                        "Candidate_ID", "Name", "Source", "Top_Skills", "Resume", "Location", "Current_Organization",
                        "Screener_Name", "Screener_Comments", "First_Interviewer_Name", "First_Interviewer_Comments",
                        "Identified_for_Roles", "Years_of_Experience", "Current_CTC"
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                '''
                run_sql(query, (
                    entry_id, name, source, top_skills, resume_uploaded_path, location, current_org,
                    screener_name, screener_comments, first_interviewer, first_interviewer_comments,
                    identified_roles_str, years_exp, current_ctc
                ))
                st.success(f'Resume for {name} added!')
                st.rerun()
    with tab3:
        if df_resumes.empty:
            st.info('No resumes available to update.')
        else:
            selected = st.selectbox('Select resume to update', df_resumes['Name'])
            resume_row = df_resumes[df_resumes['Name'] == selected].iloc[0]
            with st.form('update_resume'):
                st.info(f"Updating resume for: {selected} (Candidate_ID: {resume_row['Candidate_ID']})")
                source = st.text_input('Source', resume_row['Source'])
                top_skills = st.text_input('Top Skills', resume_row['Top_Skills'])
                location = st.text_input('Location', resume_row['Location'])
                current_org = st.text_input('Current organization', resume_row['Current_Organization'])
                screener_name = st.text_input('Screener Name', resume_row['Screener_Name'])
                screener_comments = st.text_area('Screener comments', resume_row['Screener_Comments'])
                first_interviewer = st.text_input('First Interviewer name', resume_row['First_Interviewer_Name'])
                first_interviewer_comments = st.text_area('First interviewer comments', resume_row['First_Interviewer_Comments'])
                prev_roles = set(resume_row['Identified_for_Roles'].split(';')) if resume_row['Identified_for_Roles'] and resume_row['Identified_for_Roles'] != 'No Role' else set()
                valid_prev_roles = [role for role in prev_roles if role in opp_choices]
                identified_roles = st.multiselect('Identified for roles', opp_choices, valid_prev_roles)
                added_opps = set(identified_roles) - set(valid_prev_roles)
                years_exp = st.text_input('Years of experience', resume_row['Years_of_Experience'])
                current_ctc = st.text_input('Current CTC', resume_row['Current_CTC'])
                resume_file = st.file_uploader('Upload resume to change the uploaded file')
                submitted = st.form_submit_button('Update')
                delete_clicked = st.form_submit_button('Delete')
                if submitted:
                    resume_uploaded_path = resume_row['Resume']
                    if resume_file:
                        resume_uploaded_path = file_upload_obj.outlook_file_uploader(selected, resume_file)
                    identified_roles_str = 'No Role' if not identified_roles else ';'.join(identified_roles)
                    query = '''
                        UPDATE resumes SET
                            "Source" = %s,
                            "Top_Skills" = %s,
                            "Resume" = %s,
                            "Location" = %s,
                            "Current_Organization" = %s,
                            "Screener_Name" = %s,
                            "Screener_Comments" = %s,
                            "First_Interviewer_Name" = %s,
                            "First_Interviewer_Comments" = %s,
                            "Identified_for_Roles" = %s,
                            "Years_of_Experience" = %s,
                            "Current_CTC" = %s
                        WHERE "Candidate_ID" = %s;
                    '''
                    added_opps = set(identified_roles) - set(valid_prev_roles)
                    removed_opps = set(valid_prev_roles) - set(identified_roles)
                    for opp in added_opps:
                        opp_id = opp.split(':')[-1].rstrip(')')
                        run_sql('UPDATE opportunities SET "Number_of_Candidates_Shared" = "Number_of_Candidates_Shared" + 1 WHERE "Opportunity_ID" = %s;',(opp_id,))
                    for opp in removed_opps:
                        opp_id = opp.split(':')[-1].rstrip(')')
                        run_sql('UPDATE opportunities SET "Number_of_Candidates_Shared" = GREATEST("Number_of_Candidates_Shared" - 1, 0) WHERE "Opportunity_ID" = %s;', (opp_id,))

                    run_sql(query, (
                        source, top_skills, resume_uploaded_path, location, current_org, screener_name,
                        screener_comments, first_interviewer, first_interviewer_comments,
                        identified_roles_str, years_exp, current_ctc, resume_row['Candidate_ID']
                    ))
                    st.success(f'Resume for {selected} updated!')
                    st.rerun()
                if delete_clicked:
                    query = 'DELETE FROM resumes WHERE "Candidate_ID" = %s;'
                    run_sql(query, (resume_row['Candidate_ID'],))
                    st.warning(f'Resume for {selected} deleted!')
                    st.rerun()


