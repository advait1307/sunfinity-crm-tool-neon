import msal
import requests
import urllib.parse

class OneDriveJDUploader:
    def __init__(self, config):
        self.config = config
        self.client_id = self.config['onedrive']['client_id']
        self.client_secret = self.config['onedrive']['client_secret']
        self.tenant_id = self.config['onedrive']['tenant_id']
        self.user_email = self.config['onedrive']['user_email']
        self.user_id = self.config['onedrive']['user_id']
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scope = ["https://graph.microsoft.com/.default"]
        self.access_token = self.get_token()

    def get_token(self):
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )
        result = app.acquire_token_for_client(scopes=self.scope)
        if "access_token" in result:
            return result["access_token"]
        else:
            return None

    def create_folder(self, company, uploaded_file):
        if uploaded_file is not None and company and self.user_id:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/pdf"
            }
            company_folder = company.replace(" ", "")
            url = f"https://graph.microsoft.com/v1.0/users/{self.user_id}/drive/root:/JobDescription:/children"
            response = requests.post(
                url,
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "name": f"{company_folder}",
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "replace"
                }
            )
            return response.status_code in (200, 201)
        return False

    def upload_file(self, company, role, date, oppid, uploaded_file):
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/pdf"
        }
        folder_path = f"JobDescription/{company.replace(' ', '')}"
        folder_path_encoded = urllib.parse.quote(folder_path)
        uploaded_file.name = f'{company}_{role}_{oppid}_{date}_JD.pdf'
        file_path = f"{folder_path_encoded}/{uploaded_file.name}"
        upload_url = f"https://graph.microsoft.com/v1.0/users/{self.user_id}/drive/root:/{file_path}:/content"
        uploaded_file.seek(0)
        response = requests.put(upload_url, headers=headers, data=uploaded_file)
        if response.status_code in [200, 201]:
            item_id = response.json().get('id')
            link_url = f"https://graph.microsoft.com/v1.0/users/{self.user_id}/drive/items/{item_id}/createLink"
            link_response = requests.post(
                link_url,
                headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
                json={"type": "view", "scope": "anonymous"}
            )
            if link_response.status_code in (200, 201):
                web_url = link_response.json()["link"]["webUrl"]
                return web_url
        return 'NaN'

    def outlook_jd_uploader(self, company, role, date, oppid, uploaded_file):
        company = company.strip().replace(" ", "_")
        role = role.strip().replace(" ", "_")
        date = date.strip().replace(" ", "_")
        uploaded_file.name = uploaded_file.name.replace(" ", "_")
        if self.access_token:
            if self.create_folder(company, uploaded_file):
                return self.upload_file(company, role,date, oppid, uploaded_file)
            else:
                return 'Nan'
