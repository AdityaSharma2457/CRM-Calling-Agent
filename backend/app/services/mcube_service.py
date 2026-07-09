import requests
import uuid
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class MCubeService:
    def __init__(self):
        self.api_key = settings.MCUBE_API_KEY
        self.exe_number = settings.MCUBE_EXE_NUMBER
        self.outbound_url = settings.MCUBE_OUTBOUND_API_URL

    def make_call(self, to_number: str) -> str:
        """
        Initiates an outbound call using MCube's Click-to-Call API.
        It first dials the executive/agent (exenumber) and then bridges
        the call to the customer (custnumber).
        """
        ref_id = str(uuid.uuid4())
        
      # Formulate the payload
        payload = {
            "exenumber": self.exe_number,
            "custnumber": to_number,
            "refurl": "1",
            "refid": ref_id
        }
        
        headers = {
            "HTTP_AUTHORIZATION": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        logger.info(f"Initiating MCube Click2Call. Agent: {self.exe_number}, Customer: {to_number}, RefID: {ref_id}")
        
        try:
            response = requests.post(self.outbound_url, data=payload, headers=headers)
            
            if response.status_code == 200:
                response_json = response.json()
                logger.info(f"MCube Click2Call response: {response_json}")
                # MCube typically returns a confirmation JSON payload with a status/call-id or success message.
                # If there's a call/interaction ID or similar, return it, otherwise return ref_id.
                call_id = response_json.get("callid") or response_json.get("msg") or ref_id
                return str(call_id)
            else:
                logger.error(f"MCube API error status code {response.status_code}: {response.text}")
                # Fall back to returning ref_id or raising an exception
                response.raise_for_status()
                return ref_id
        except Exception as e:
            logger.exception("Failed to make outbound call with MCube")
            raise e
