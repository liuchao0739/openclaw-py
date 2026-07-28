from typing import Dict
import time
import webbrowser


async def runGitHubCopilotDeviceFlow(params: Dict) -> Dict:
    import requests

    response = requests.post("https://github.com/login/device/code", data={
        "client_id": "Iv1.b507a10543625d19",
        "scope": "read:user",
    })
    data = response.json()

    verificationUrl = data.get("verification_uri")
    userCode = data.get("user_code")
    deviceCode = data.get("device_code")
    expiresInMs = data.get("expires_in", 900) * 1000
    interval = data.get("interval", 5)

    await params["showCode"]({
        "verificationUrl": verificationUrl,
        "userCode": userCode,
        "expiresInMs": expiresInMs,
    })

    await params["openUrl"](verificationUrl)

    startTime = time.time() * 1000
    while time.time() * 1000 - startTime < expiresInMs:
        response = requests.post("https://github.com/login/oauth/access_token", data={
            "client_id": "Iv1.b507a10543625d19",
            "device_code": deviceCode,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })
        tokenData = response.json()

        if "access_token" in tokenData:
            return {
                "status": "success",
                "accessToken": tokenData["access_token"],
            }

        if tokenData.get("error") == "access_denied":
            return {"status": "access_denied"}

        if tokenData.get("error") == "expired_token":
            return {"status": "expired"}

        time.sleep(interval)

    return {"status": "expired"}

__all__ = ["runGitHubCopilotDeviceFlow"]