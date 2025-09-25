import msal
import requests
import urllib.parse

class OneDriveUploader:
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

    def create_folder(self, candidate, uploaded_file):
        if uploaded_file is not None and candidate and self.user_id:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/pdf"
            }
            candidate_folder = candidate.replace(" ", "")
            url = f"https://graph.microsoft.com/v1.0/users/{self.user_id}/drive/root:/Resumes:/children"
            response = requests.post(
                url,
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "name": f"{candidate_folder}",
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "replace"
                }
            )
            return response.status_code in (200, 201)
        return False

    def upload_file(self, candidate, uploaded_file):
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/pdf"
        }
        folder_path = f"Resumes/{candidate}"
        folder_path_encoded = urllib.parse.quote(folder_path)
        uploaded_file.name = f'{candidate}_resume.pdf'
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

    def outlook_file_uploader(self, candidate, uploaded_file):
        candidate = candidate.strip().replace(" ", "_")
        uploaded_file.name = uploaded_file.name.replace(" ", "_")
        if self.access_token:
            if self.create_folder(candidate, uploaded_file):
                return self.upload_file(candidate, uploaded_file)
            else:
                return 'NaN'


